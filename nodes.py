"""PocketFlow 节点：只做编排，具体规则在 core/ 下。

流水线（与 3GPP 测试设计过程对应）：
    需求解析 → 三方评审 → 综合定稿           （测试需求分析，HITL 多轮）
    → 测试设计：测试目标 + 按测试技术导出的整合矩阵（每行一个测试点，带 TP）
    → 设计质量门：确定性补入需求配置/数值门限，缺覆盖时只为缺口补行
    → 测试用例：每个测试点写成 3GPP 风格测试用例描述（TCD），分批并行，输出过长自动拆批
    → 用例质量门：补入需求配置和数值门限 + LLM 专家评审，只返工有问题的用例
    → 可执行用例（exec_cases.py）：由 TCD 投影草稿，LLM 做平台适配

调用 LLM 的节点都把阻塞请求放到线程池（ThreadedNode / asyncio.to_thread），生成过程中服务仍能响应其他请求和推送进度。
"""
import asyncio
import datetime as dt
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from pocketflow import AsyncNode, Node
from schemas import (
    DEFAULT_ACTION_VOCABULARY,
    DEFAULT_ASSERTION_VOCABULARY,
    DEFAULT_CAPABILITIES,
    INTEGRATED_MATRIX_SCHEMA,
    PERSONA_REVIEW_SCHEMA,
    REQUIREMENT_LIST_SCHEMA,
    SYNTHESIS_SCHEMA,
    TESTCASE_REQUIRED_KEYS,
    TEST_DESIGN_SCHEMA,
    TEST_OBJECTIVE_REQUIRED_KEYS,
)
from core import environments as envs
from core.events import emit as _emit
from core.grouping import attach_suites, restore_groups
from core.llm import MAX_CONCURRENCY, generate_json, generate_json_or_fallback, run_split_on_truncate
from core.quality import (
    design_advice,
    design_gaps,
    feedback_for_rows,
    merge_expert_review,
    repair_design_rows,
    req_index,
    req_metrics,
    review_stats,
    review_testcases,
    rows_for_tcs,
    split_tcs_by_rows,
)
from core.tcd import TCD_LIST_SCHEMA, TECHNIQUES, normalize_tcd, normalize_technique, renumber, summarize_for_prompt
from utils.req_configs import normalize_explicit_configs, restore_explicit_configs
from utils.schema_validation import validate_jsonschema, validate_list_of_dict

NODE_LABELS = {
    "IntakeNode": "需求录入",
    "ReqParseNode": "需求解析",
    "TriPersonaReviewNode": "三方评审",
    "SynthesisNode": "综合定稿",
    "TestDesignNode": "测试设计",
    "TestDesignSupervisorNode": "设计质量门",
    "TestCaseBatchGenNode": "编写测试用例",
    "FinalizeTestCaseNode": "汇总测试用例",
    "TestCaseSupervisorNode": "用例质量门与专家评审",
    "ExecutableCaseNode": "生成可执行用例",
    "AssembleResultNode": "汇总结果",
}
KNOWLEDGE_CHARS_FOR_CASES = 6000


def _req_batch_size() -> int:
    try:
        return max(1, int(os.getenv("TESTFLOW_REQ_BATCH_SIZE") or 8))
    except ValueError:
        return 8


def _req_batches(reqs: List[Any]) -> List[List[Any]]:
    """需求分析和测试设计按需求分批调用模型。

    一次把几十条需求塞进一个请求，输出很容易超长被截断，后面的需求也会越写越粗。
    条数不超过一批时只有一批，行为与不分批相同。
    """
    reqs, size = list(reqs or []), _req_batch_size()
    return [reqs[i:i + size] for i in range(0, len(reqs), size)] or [[]]


def _map_batches(fn, batches: List[Any]) -> List[Any]:
    """按原顺序返回各批结果；多批时并行（总并发仍受 core.llm 的全局限流约束）。"""
    if len(batches) <= 1:
        return [fn(b) for b in batches]
    with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENCY, len(batches))) as pool:
        return list(pool.map(fn, batches))


def _batch_tag(tag: str, idx: int, total: int) -> str:
    return tag if total <= 1 else f"{tag}-Batch{idx}"


def _merge_unique(lists: List[Any]) -> List[Any]:
    out, seen = [], set()
    for items in lists:
        for x in items or []:
            key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x)
            if key not in seen:
                seen.add(key)
                out.append(x)
    return out


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _trace(shared: Dict[str, Any], node: str):
    shared.setdefault("trace", []).append({"node": node, "time": _now()})


def _set_current_node(shared: Dict[str, Any], node: str, detail: str = ""):
    shared["current_node"] = node
    _emit(shared, "node_running", {"node": node, "label": NODE_LABELS.get(node, node), "detail": detail})


def _warn(shared: Dict[str, Any], text: str):
    shared.setdefault("warnings", []).append(text)


def _confirmed_answers(shared: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"question": q.get("question", ""), "answer": q.get("answer", ""), "source": q.get("source", "用户")}
        for q in ((shared.get("requirement_review_history") or {}).get("answered_questions") or [])
        if isinstance(q, dict)
    ]


def _requirement_view(req: Dict[str, Any]) -> Dict[str, Any]:
    view = {k: req.get(k) for k in ("req_id", "title", "feature", "rat_scope", "preconditions", "trigger", "expected",
                                    "constraints", "priority") if req.get(k)}
    acc = req.get("acceptance") or {}
    if isinstance(acc, dict) and (acc.get("pass_fail") or acc.get("kpi")):
        view["acceptance"] = {k: acc.get(k) for k in ("pass_fail", "kpi") if acc.get(k)}
    cfgs = normalize_explicit_configs(req)
    if cfgs:
        view["explicit_configs"] = [{k: v for k, v in c.items() if k != "req_id"} for c in cfgs]
    return view


class ThreadedNode(AsyncNode):
    """prep / post 在事件循环里执行，exec（阻塞的 LLM 请求）放到线程池。子类照常写同步的 prep / exec / post。"""

    async def prep_async(self, shared):
        self._shared = shared
        return self.prep(shared)

    async def exec_async(self, prep_res):
        return await asyncio.to_thread(self.exec, prep_res)

    async def post_async(self, shared, prep_res, exec_res):
        return self.post(shared, prep_res, exec_res)


class IntakeNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "IntakeNode")
        return {
            "requirements": shared.get("input_requirements", []),
            "requirement_meta": shared.get("requirement_meta") or [],
            "rag_context": shared.get("rag_context", ""),
            "review_feedback": shared.get("review_feedback", ""),
            "framework_capability_catalog": shared.get("framework_capability_catalog", ""),
            "product_profile": shared.get("product_profile", {}),
            "action_vocabulary": shared.get("action_vocabulary") or DEFAULT_ACTION_VOCABULARY,
            "assertion_vocabulary": shared.get("assertion_vocabulary") or DEFAULT_ASSERTION_VOCABULARY,
            "capabilities": shared.get("capabilities") or DEFAULT_CAPABILITIES,
        }

    def exec(self, prep_res):
        raw = list(prep_res["requirements"] or [])
        metas = list(prep_res.get("requirement_meta") or [])
        metas = metas if len(metas) == len(raw) else []  # 与需求一一对应才可信
        pairs = [(x.strip(), metas[i] if metas and isinstance(metas[i], dict) else {})
                 for i, x in enumerate(raw) if x and x.strip()]
        if not pairs:
            raise ValueError("requirements不能为空")

        items = []
        used_ids, renamed = set(), []
        for idx, (text, meta) in enumerate(pairs, start=1):
            req_id = " ".join(str(meta.get("req_id") or "").split()) or f"REQ-{idx:03d}"
            if req_id in used_ids:  # 清单里编号重复：加后缀保证唯一，否则后面的追溯会把两条需求混在一起
                base, n = req_id, 2
                while f"{base}-{n}" in used_ids:
                    n += 1
                req_id = f"{base}-{n}"
                renamed.append(f"{base} → {req_id}")
            used_ids.add(req_id)
            group = [str(g).strip() for g in (meta.get("group") or []) if str(g).strip()][:2]
            items.append(
                {
                    "req_id": req_id,
                    **({"group": group} if group else {}),
                    "title": text,
                    "source": {
                        "type": "PRD",
                        "doc_id": "USER_INPUT",
                        "section": "N/A",
                        "lang": "mixed",
                        "evidence_refs": [],
                    },
                    "feature": "MODEM_SYSTEM",
                    "rat_scope": ["5G", "IMS"],
                    "preconditions": ["待补充"],
                    "trigger": ["待补充"],
                    "expected": ["待补充"],
                    "acceptance": {"pass_fail": ["待补充"], "kpi": []},
                    "constraints": [],
                    "observability": {
                        "signals": [],
                        "logs": ["modem_log", "logcat"],
                        "counters": [],
                        "must_capture": ["modem_log", "logcat"],
                    },
                    "priority": "P1",
                    "open_questions": [],
                    "assumptions": [],
                }
            )

        return {
            "seed_requirements": items,
            "_renamed_req_ids": renamed,
            "rag_context": prep_res["rag_context"].strip(),
            "review_feedback": prep_res["review_feedback"].strip(),
            "framework_capability_catalog": prep_res["framework_capability_catalog"].strip(),
            "product_profile": prep_res.get("product_profile") or {},
            "action_vocabulary": prep_res["action_vocabulary"],
            "assertion_vocabulary": prep_res["assertion_vocabulary"],
            "capabilities": prep_res["capabilities"],
        }

    def post(self, shared, prep_res, exec_res):
        renamed = exec_res.pop("_renamed_req_ids", [])
        if renamed:
            _warn(shared, "IntakeNode: 需求清单里有重复的需求编号，已加后缀区分：" + "；".join(renamed))
        shared.update(exec_res)
        missing_inputs = []
        if not exec_res["rag_context"]:
            missing_inputs.append("缺少RAG文档上下文（3GPP/运营商/历史缺陷等）")
        if not exec_res["framework_capability_catalog"]:
            missing_inputs.append("缺少测试脚本框架能力清单（驱动、日志采集、报告能力）")
        shared["missing_inputs"] = missing_inputs
        _trace(shared, "IntakeNode")
        return "default"


class ReqParseNode(ThreadedNode):
    def prep(self, shared):
        _set_current_node(shared, "ReqParseNode")
        return {
            "seed_requirements": shared["seed_requirements"],
            "rag_context": shared.get("rag_context", ""),
            "review_feedback": shared.get("review_feedback", ""),
            "product_profile": shared.get("product_profile", {}),
        }

    def exec(self, prep_res):
        batches = _req_batches(prep_res["seed_requirements"])

        def _parse(item):
            idx, seeds = item
            if len(batches) > 1:
                _set_current_node(self._shared, "ReqParseNode", f"第 {idx}/{len(batches)} 批（共 {len(prep_res['seed_requirements'])} 条需求）")
            out = generate_json_or_fallback(
                shared=self._shared,
                template_name="req_parse.txt",
                variables={
                    "glossary_json": json.dumps({"attach": "注册", "idle reselection": "驻留重选"}, ensure_ascii=False),
                    "doc_meta_json": json.dumps({"type": "USER_INPUT", "lang": "mixed"}, ensure_ascii=False),
                    "text_chunk": json.dumps(seeds, ensure_ascii=False),
                    "rag_context": prep_res.get("rag_context", ""),
                    "review_feedback": prep_res.get("review_feedback", ""),
                    "product_profile_json": json.dumps(prep_res.get("product_profile", {}), ensure_ascii=False),
                    "output_schema": json.dumps(REQUIREMENT_LIST_SCHEMA, ensure_ascii=False),
                },
                schema=REQUIREMENT_LIST_SCHEMA,
                fallback=seeds,
                warn_tag=_batch_tag("ReqParseNode", idx, len(batches)),
            )
            return list(out) if isinstance(out, list) else list(seeds)

        return [req for part in _map_batches(_parse, list(enumerate(batches, start=1))) for req in part]

    def post(self, shared, prep_res, exec_res):
        validate_jsonschema(exec_res, REQUIREMENT_LIST_SCHEMA)
        # Preserve coverage from input list: if model collapses items, append missing seeds.
        if len(exec_res) < len(prep_res["seed_requirements"]):
            seen_ids = {x.get("req_id") for x in exec_res if isinstance(x, dict)}
            for seed in prep_res["seed_requirements"]:
                if seed.get("req_id") not in seen_ids:
                    exec_res.append(seed)
            shared.setdefault("warnings", []).append(
                "ReqParseNode: LLM压缩了需求条目，已补齐缺失条目以保持覆盖。"
            )
        restore_groups(exec_res, prep_res["seed_requirements"])
        shared["requirements_parsed"] = exec_res
        _trace(shared, "ReqParseNode")
        _emit(shared, "module_result", {"module": "req_parse", "data": exec_res})
        return "default"


_PRIORITIES = ("P0", "P1", "P2")


def _normalize_review_questions(review: Any) -> None:
    """把评审输出的 open_questions 统一成两份：
    open_questions 保持字符串列表（页面、文档、Excel 都按字符串展示），
    question_details 保存优先级、是否需要用户确认、AI 的默认答案，供问题分级使用。"""
    if not isinstance(review, dict):
        return
    for item in review.get("reviews", []) or []:
        if not isinstance(item, dict):
            continue
        details = []
        for q in item.get("open_questions", []) or []:
            if isinstance(q, str):
                d = {"question": q.strip(), "priority": "P1", "needs_user": True, "ai_answer": "", "basis": ""}
            elif isinstance(q, dict):
                pr = str(q.get("priority") or "P1").upper().strip()
                d = {
                    "question": str(q.get("question") or q.get("q") or "").strip(),
                    "priority": pr if pr in _PRIORITIES else "P1",
                    "needs_user": q.get("needs_user") is not False and str(q.get("needs_user")).lower() != "false",
                    "ai_answer": str(q.get("ai_answer") or q.get("assumption") or "").strip(),
                    "basis": str(q.get("basis") or "").strip(),
                }
            else:
                continue
            if d["question"]:
                details.append(d)
        item["question_details"] = details
        item["open_questions"] = [d["question"] for d in details]


class TriPersonaReviewNode(AsyncNode):
    async def prep_async(self, shared):
        _set_current_node(shared, "TriPersonaReviewNode")
        return {"requirements": shared["requirements_parsed"]}

    async def _review_persona(self, shared: Dict[str, Any], template: str, role: str, requirements: List[Dict[str, Any]],
                              tag: str = ""):
        fallback = {
            "reviews": [
                {
                    "req_id": r["req_id"],
                    "issues": [f"{role}: 需补充量化验收标准"],
                    "rewrite_suggestion": "补充可测量阈值、状态机前置条件与日志证据",
                    "scores": {"correctness_risk": 3, "testability_gap": 3, "ambiguity_level": 3},
                    "must_observe": r.get("observability", {}).get("must_capture", []),
                    "open_questions": [{"question": "请确认通过/失败阈值", "priority": "P1", "needs_user": True,
                                        "ai_answer": "", "basis": ""}],
                }
                for r in requirements
            ]
        }

        return await asyncio.to_thread(
            generate_json_or_fallback,
            shared=shared,
            template_name=template,
            variables={
                "requirements_json": json.dumps(requirements, ensure_ascii=False),
                "history_risk_json": json.dumps([], ensure_ascii=False),
                "return_schema": json.dumps(PERSONA_REVIEW_SCHEMA, ensure_ascii=False),
                "output_schema": json.dumps(PERSONA_REVIEW_SCHEMA, ensure_ascii=False),
            },
            schema=PERSONA_REVIEW_SCHEMA,
            fallback=fallback,
            warn_tag=tag or f"TriPersonaReviewNode-{role}",
        )

    async def _review_in_batches(self, shared, template: str, role: str, requirements: List[Dict[str, Any]]):
        batches = _req_batches(requirements)
        if len(batches) == 1:
            return await self._review_persona(shared, template, role, requirements)
        parts = await asyncio.gather(*[
            self._review_persona(shared, template, role, b, tag=f"TriPersonaReviewNode-{role}-Batch{i}")
            for i, b in enumerate(batches, start=1)])
        return {"reviews": [r for p in parts for r in (p.get("reviews") or [])]}

    async def exec_async(self, prep_res):
        reqs = prep_res["requirements"]
        shared = self._shared
        spec_task = self._review_in_batches(shared, "review_spec_lawyer.txt", "SpecLawyer", reqs)
        carrier_task = self._review_in_batches(shared, "review_carrier.txt", "CarrierReviewer", reqs)
        ux_task = self._review_in_batches(shared, "review_ux_advocate.txt", "UXAdvocate", reqs)
        spec, carrier, ux = await asyncio.gather(spec_task, carrier_task, ux_task)
        return {"spec": spec, "carrier": carrier, "ux": ux}

    async def post_async(self, shared, prep_res, exec_res):
        for review in exec_res.values():
            _normalize_review_questions(review)
        validate_jsonschema(exec_res["spec"], PERSONA_REVIEW_SCHEMA)
        validate_jsonschema(exec_res["carrier"], PERSONA_REVIEW_SCHEMA)
        validate_jsonschema(exec_res["ux"], PERSONA_REVIEW_SCHEMA)
        shared["persona_reviews"] = exec_res
        _trace(shared, "TriPersonaReviewNode")
        _emit(shared, "module_result", {"module": "persona_reviews", "data": exec_res})
        return "default"

    async def _run_async(self, shared):
        self._shared = shared
        return await super()._run_async(shared)


class SynthesisNode(ThreadedNode):
    def prep(self, shared):
        _set_current_node(shared, "SynthesisNode")
        return {"requirements": shared["requirements_parsed"], "reviews": shared["persona_reviews"]}

    def exec(self, prep_res):
        batches = _req_batches(prep_res["requirements"])
        reviews = prep_res["reviews"]

        def _reviews_for(persona: str, ids: set) -> Dict[str, Any]:
            data = reviews.get(persona) or {}
            if len(batches) == 1:
                return data
            return {**data, "reviews": [r for r in data.get("reviews") or []
                                        if isinstance(r, dict) and str(r.get("req_id")) in ids]}

        def _synthesize(item):
            idx, reqs = item
            ids = {str(r.get("req_id")) for r in reqs if isinstance(r, dict)}
            if len(batches) > 1:
                _set_current_node(self._shared, "SynthesisNode", f"第 {idx}/{len(batches)} 批")
            fallback = {
                "final_requirements": reqs,
                "conflicts": [],
                "questions_to_ask": ["请确认每条需求的量化通过标准"],
                "assumptions": ["默认按P1执行，待业务确认后升降级"],
            }
            return generate_json_or_fallback(
                shared=self._shared,
                template_name="synthesis_arbiter.txt",
                variables={
                    "requirements_json": json.dumps(reqs, ensure_ascii=False),
                    "reviews_spec_json": json.dumps(_reviews_for("spec", ids), ensure_ascii=False),
                    "reviews_carrier_json": json.dumps(_reviews_for("carrier", ids), ensure_ascii=False),
                    "reviews_ux_json": json.dumps(_reviews_for("ux", ids), ensure_ascii=False),
                    "return_schema": json.dumps(SYNTHESIS_SCHEMA, ensure_ascii=False),
                    "output_schema": json.dumps(SYNTHESIS_SCHEMA, ensure_ascii=False),
                },
                schema=SYNTHESIS_SCHEMA,
                fallback=fallback,
                warn_tag=_batch_tag("SynthesisNode", idx, len(batches)),
            )

        parts = _map_batches(_synthesize, list(enumerate(batches, start=1)))
        if len(parts) == 1:
            return parts[0]
        merged = dict(parts[0])
        merged["final_requirements"] = [r for p in parts for r in (p.get("final_requirements") or [])]
        for key in ("conflicts", "questions_to_ask", "assumptions"):
            merged[key] = _merge_unique([p.get(key) for p in parts])
        return merged

    def post(self, shared, prep_res, exec_res):
        validate_jsonschema(exec_res, SYNTHESIS_SCHEMA)
        restored = restore_explicit_configs(exec_res.get("final_requirements", []), prep_res["requirements"])
        if restored:
            shared.setdefault("warnings", []).append(
                f"SynthesisNode: 综合评审丢失了 {restored} 项需求显式配置，已按 req_id 补回。")
        restore_groups(exec_res.get("final_requirements", []), prep_res["requirements"])
        for req in exec_res.get("final_requirements", []):
            if isinstance(req, dict):
                req["persona_sources"] = req.get("persona_sources") or ["PRD", "Carrier", "UX"]
        shared["requirement_spec"] = exec_res
        _trace(shared, "SynthesisNode")
        _emit(shared, "module_result", {"module": "requirement_spec", "data": exec_res})
        return "default"



# ---------- 测试设计：规范化 ----------


def _normalize_objectives(data: Dict[str, Any], final_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
    req_ids = [r.get("req_id") for r in final_requirements if isinstance(r, dict) and r.get("req_id")]
    norm = []
    for idx, obj in enumerate(data.get("objectives", []) or [], start=1):
        if not isinstance(obj, dict):
            continue
        linked = obj.get("linked_reqs") or obj.get("req_ids") or req_ids[:1] or [f"REQ-{idx:03d}"]
        evidence = obj.get("evidence") or obj.get("must_capture") or ["modem_log"]
        if isinstance(evidence, dict):
            evidence = evidence.get("must_capture", []) or ["modem_log"]
        norm.append({
            "objective_id": obj.get("objective_id") or obj.get("objectiveId") or obj.get("id") or f"TO-{idx:03d}",
            "linked_reqs": linked if isinstance(linked, list) else [linked],
            "goal": obj.get("goal") or obj.get("title") or obj.get("objective") or f"测试目标-{idx}",
            "success_criteria": obj.get("success_criteria") or obj.get("pass_fail") or ["主流程成功"],
            "evidence": evidence,
            "priority": obj.get("priority") or "P1",
            "risk_notes": obj.get("risk_notes") or obj.get("risk") or "",
        })
    data["objectives"] = norm
    norm_cms = []
    for idx, cm in enumerate(data.get("coverage_matrices", []) if isinstance(data.get("coverage_matrices"), list) else [], start=1):
        if not isinstance(cm, dict):
            continue
        dims = cm.get("dimensions", [])
        if isinstance(dims, dict):
            dims = [{"name": k, "values": v if isinstance(v, list) else [v]} for k, v in dims.items()]
        norm_cms.append({
            "matrix_id": cm.get("matrix_id") or cm.get("matrixId") or f"CM-{idx:03d}",
            "dimensions": dims if isinstance(dims, list) else [],
            "sampling_strategy": cm.get("sampling_strategy") or cm.get("sampling") or {"type": "pairwise"},
        })
    data["coverage_matrices"] = norm_cms
    data.setdefault("design_notes", [])
    data.setdefault("de_scoped", [])
    return data


def _norm_purpose(raw: Any, scenario: str) -> Dict[str, str]:
    if isinstance(raw, str):
        raw = {"then": raw}
    raw = raw if isinstance(raw, dict) else {}
    return {"with": str(raw.get("with") or ""), "when": str(raw.get("when") or ""), "then": str(raw.get("then") or scenario)}


def _normalize_integrated_rows(rows: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]],
                               objectives: List[Dict[str, Any]], available_envs: Any = None,
                               start_index: int = 1) -> List[Dict[str, Any]]:
    obj_map = {o.get("objective_id"): o for o in objectives if isinstance(o, dict)}
    known_reqs = set(req_index(final_requirements))
    norm = []
    for idx, r in enumerate(rows or [], start=start_index):
        if not isinstance(r, dict):
            continue
        obj = obj_map.get(r.get("objective_id"), {})
        cfg = r.get("key_configuration") if isinstance(r.get("key_configuration"), dict) else {}
        scenario = str(r.get("scenario") or "").strip() or obj.get("goal", "目标验证")
        if scenario == obj.get("goal") and cfg:
            scenario = f"{scenario} @ " + "/".join(str(v) for v in list(cfg.values())[:3])
        crit = r.get("pass_criteria", [])
        crit = [str(c) for c in (crit if isinstance(crit, list) else [crit]) if str(c).strip()]
        technique, technique_raw = normalize_technique(r.get("technique"))
        req_id = str(r.get("req_id") or "")
        if req_id not in known_reqs:  # 没写或写错需求编号时，按所属目标关联的需求归位，避免这行游离在追溯之外
            req_id = next((x for x in obj.get("linked_reqs") or [] if x in known_reqs), req_id)
        norm.append({
            "row_id": str(r.get("row_id") or f"ROW-{idx:03d}"),
            "req_id": req_id,
            "objective_id": r.get("objective_id") or next(
                (o["objective_id"] for o in objectives if req_id in (o.get("linked_reqs") or [])), ""),
            "technique": technique,
            **({"technique_raw": technique_raw} if technique_raw else {}),
            "scenario": scenario,
            "test_purpose": _norm_purpose(r.get("test_purpose"), scenario),
            "key_configuration": cfg,
            "pass_criteria": crit or ["关键指标满足需求标准"],
            "references": [str(x) for x in (r.get("references") or []) if str(x).strip()],
            "test_environment": envs.normalize_env(r.get("test_environment"), [scenario] + crit, available_envs),
        })
    return norm


def _dedupe_row_ids(rows: List[Dict[str, Any]]) -> None:
    seen = set()
    for n, row in enumerate(rows, start=1):
        if row["row_id"] in seen:
            row["row_id"] = next(c for c in (f"ROW-{k:03d}" for k in range(n, n + len(rows) + 1)) if c not in seen)
        seen.add(row["row_id"])


def _fallback_rows(missing_reqs: List[str], missing_objs: List[str], final_requirements: List[Dict[str, Any]],
                   objectives: List[Dict[str, Any]], available_envs: Any, start: int) -> List[Dict[str, Any]]:
    """规则兜底：每个缺口一行正常流程，保证追溯完整。缺目标的需求顺带建一个目标（追加到 objectives）。"""
    reqs = req_index(final_requirements)
    obj_by_id = {o["objective_id"]: o for o in objectives}
    rows = []
    for oid in missing_objs:
        o = obj_by_id.get(oid, {})
        rid = (o.get("linked_reqs") or [""])[0]
        rows.append((rid, oid, o.get("goal", "")))
    for rid in missing_reqs:
        if any(r[0] == rid for r in rows):
            continue
        oid = next((o["objective_id"] for o in objectives if rid in (o.get("linked_reqs") or [])), "")
        if not oid:
            oid = f"TO-{len(objectives) + 1:03d}"
            req = reqs.get(rid, {})
            objectives.append({"objective_id": oid, "linked_reqs": [rid], "goal": req.get("title", rid),
                               "success_criteria": req_metrics(req) or ["主流程成功"], "evidence": ["modem_log"],
                               "priority": req.get("priority", "P1"), "risk_notes": "按规则生成的目标"})
        rows.append((rid, oid, reqs.get(rid, {}).get("title", "")))
    out = []
    for i, (rid, oid, goal) in enumerate(rows, start=start):
        req = reqs.get(rid, {})
        texts = [goal] + [str(x) for x in (req.get("trigger") or []) + (req.get("expected") or [])]
        out.append({"row_id": f"ROW-{i:03d}", "req_id": rid, "objective_id": oid, "technique": "normal",
                    "scenario": goal or rid,
                    "test_purpose": {"with": "；".join(str(x) for x in req.get("preconditions") or [] if x != "待补充"),
                                     "when": "；".join(str(x) for x in req.get("trigger") or [] if x != "待补充"),
                                     "then": "；".join(str(x) for x in req.get("expected") or [] if x != "待补充") or goal},
                    "key_configuration": {}, "pass_criteria": req_metrics(req) or ["关键指标满足需求标准"],
                    "references": [], "test_environment": envs.recommend(texts, available_envs)})
    return out


class TestDesignNode(ThreadedNode):
    def prep(self, shared):
        _set_current_node(shared, "TestDesignNode")
        spec = shared["requirement_spec"]
        return {
            "final_requirements": spec.get("final_requirements", []),
            "questions_to_ask": spec.get("questions_to_ask", []),
            "assumptions": spec.get("assumptions", []),
            "confirmed_answers": _confirmed_answers(shared),
            "product_profile": shared.get("product_profile", {}),
            "test_environments": shared.get("test_environments", {}),
            "supervisor_feedback": shared.get("design_supervisor_feedback", ""),
            "knowledge_references": shared.get("knowledge_context", ""),
        }

    def _design_by_llm(self, prep_res, tag: str = "TestDesignNode") -> Dict[str, Any]:
        def _custom(data: Any):
            if not isinstance(data.get("objectives"), list) or not data["objectives"]:
                raise ValueError("objectives 不能为空")
            if not isinstance(data.get("integrated_matrix"), list) or not data["integrated_matrix"]:
                raise ValueError("integrated_matrix 不能为空，每个目标至少一行")

        available = prep_res.get("test_environments", {})
        return generate_json(
            shared=self._shared,
            template_name="test_designer.txt",
            variables={
                "final_requirements_json": json.dumps(prep_res["final_requirements"], ensure_ascii=False),
                "constraints_json": json.dumps({
                    "questions_to_ask": prep_res.get("questions_to_ask", []),
                    "assumptions": prep_res.get("assumptions", []),
                    "confirmed_answers": prep_res.get("confirmed_answers", []),
                    "product_profile": prep_res.get("product_profile", {}),
                    "environments": envs.environment_brief(available),
                    "available_test_environments": available,
                    "supervisor_feedback": prep_res.get("supervisor_feedback", ""),
                    "knowledge_references": prep_res.get("knowledge_references", ""),
                }, ensure_ascii=False),
            },
            schema=TEST_DESIGN_SCHEMA,
            warn_tag=tag,
            custom_validator=_custom,
        )

    def _fill_gaps(self, rows, objectives, reqs, available) -> int:
        """缺覆盖的需求 / 目标：先让 LLM 只为缺口补行，仍缺的按规则补。返回补的行数。"""
        shared = self._shared
        gaps = design_gaps(rows, reqs, objectives)
        if not (gaps["missing_reqs"] or gaps["missing_objectives"]):
            return 0
        before = len(rows)
        if shared["llm_client"].enabled:
            _set_current_node(shared, "TestDesignNode", "为未覆盖的需求补充测试点")
            try:
                extra = generate_json(
                    shared=shared,
                    template_name="integrated_matrix_designer.txt",
                    variables={
                        "gaps_json": json.dumps(gaps, ensure_ascii=False),
                        "final_requirements_json": json.dumps(
                            [r for r in reqs if r.get("req_id") in gaps["missing_reqs"]] or reqs, ensure_ascii=False),
                        "objectives_json": json.dumps(objectives, ensure_ascii=False),
                        "existing_rows_json": json.dumps(
                            [{k: r[k] for k in ("row_id", "req_id", "objective_id", "technique", "scenario")} for r in rows],
                            ensure_ascii=False),
                        "available_test_environments_json": json.dumps(envs.environment_brief(available), ensure_ascii=False),
                        "next_row_id": f"ROW-{before + 1:03d}",
                    },
                    schema=INTEGRATED_MATRIX_SCHEMA,
                    warn_tag="IntegratedMatrixGapFill",
                )
                rows.extend(_normalize_integrated_rows(extra.get("integrated_matrix", []), reqs, objectives, available, before + 1))
            except Exception as exc:
                _warn(shared, f"TestDesignNode: 补漏生成失败，按规则补行: {exc}")
        gaps = design_gaps(rows, reqs, objectives)
        if gaps["missing_reqs"] or gaps["missing_objectives"]:
            rows.extend(_fallback_rows(gaps["missing_reqs"], gaps["missing_objectives"], reqs, objectives, available, len(rows) + 1))
        return len(rows) - before

    def _design_one(self, prep_res, reqs, available, tag: str, row_start: int = 1):
        """对一批需求做测试设计，返回 (规范化后的设计, 行)。"""
        data = self._design_by_llm({**prep_res, "final_requirements": reqs}, tag)
        design = _normalize_objectives(data, reqs)
        rows = _normalize_integrated_rows(data.get("integrated_matrix", []), reqs, design["objectives"], available, row_start)
        return design, rows

    def _design_in_batches(self, prep_res, reqs, available):
        """需求多时按批设计再合并。各批独立编号，合并时把撞号的目标和矩阵编号改成唯一的。"""
        batches = _req_batches(reqs)
        if len(batches) == 1:
            return self._design_one(prep_res, reqs, available, "TestDesignNode")

        def _run(item):
            idx, batch = item
            _set_current_node(self._shared, "TestDesignNode", f"第 {idx}/{len(batches)} 批（共 {len(reqs)} 条需求）")
            return self._design_one(prep_res, batch, available, f"TestDesignNode-Batch{idx}")

        parts = _map_batches(_run, list(enumerate(batches, start=1)))
        merged: Dict[str, Any] = {"objectives": [], "coverage_matrices": [], "req_to_objective_map": []}
        rows: List[Dict[str, Any]] = []
        obj_ids, cm_ids = set(), set()
        for idx, (design, part_rows) in enumerate(parts, start=1):
            rename = {}
            for obj in design["objectives"]:
                oid = obj["objective_id"]
                if oid in obj_ids:
                    rename[oid] = obj["objective_id"] = next(
                        c for c in (f"{oid}-B{idx}" + (f"-{k}" if k else "") for k in range(len(obj_ids) + 2)) if c not in obj_ids)
                obj_ids.add(obj["objective_id"])
                merged["objectives"].append(obj)
            for cm in design["coverage_matrices"]:
                if cm["matrix_id"] in cm_ids:
                    cm["matrix_id"] = f"{cm['matrix_id']}-B{idx}"
                cm_ids.add(cm["matrix_id"])
                merged["coverage_matrices"].append(cm)
            for row in part_rows:
                row["objective_id"] = rename.get(row["objective_id"], row["objective_id"])
                rows.append(row)
            for m in design.get("req_to_objective_map") or []:
                if isinstance(m, dict):
                    m["objective_ids"] = [rename.get(x, x) for x in m.get("objective_ids") or []]
                    merged["req_to_objective_map"].append(m)
        merged["design_notes"] = _merge_unique([d.get("design_notes") for d, _ in parts])
        merged["de_scoped"] = _merge_unique([d.get("de_scoped") for d, _ in parts])
        return merged, rows

    def exec(self, prep_res):
        shared = self._shared
        reqs = prep_res["final_requirements"]
        available = prep_res.get("test_environments", {})
        by_llm = bool(shared["llm_client"].enabled)
        if by_llm:
            design, rows = self._design_in_batches(prep_res, reqs, available)
        else:
            # 没配大模型时给出最小骨架（每条需求一个正常流程测试点），方便先把流程和导出走通
            _warn(shared, "TestDesignNode: LLM未配置，按规则生成最小测试设计（每条需求一个正常流程测试点）")
            design = _normalize_objectives(
                {"objectives": [], "coverage_matrices": [], "integrated_matrix": [],
                 "design_notes": ["大模型未配置：本设计由规则生成，只含正常流程骨架"], "de_scoped": []}, reqs)
            rows = []
        objectives = design["objectives"]
        gap_filled = self._fill_gaps(rows, objectives, reqs, available)
        _dedupe_row_ids(rows)
        unknown = sorted({r.pop("technique_raw") for r in rows if r.get("technique_raw")})
        if unknown:
            _warn(shared, "TestDesignNode: 以下测试技术不在支持的取值里，已按 normal 处理：" + "、".join(unknown)
                  + "（支持：" + " / ".join(TECHNIQUES) + "）")

        patched = repair_design_rows(rows, reqs)
        if patched["configs"]:
            _warn(shared, f"设计质量门: {patched['configs']} 项需求写明的配置未进矩阵，已按需求原值补入 key_configuration")
        if patched["metrics"]:
            _warn(shared, f"设计质量门: {patched['metrics']} 条需求验收门限没有测试点承接，已补入对应测试点的通过标准")
        design["integrated_matrix"] = rows
        design["design_advice"] = design_advice(rows, reqs)
        design["knowledge_references"] = str(prep_res.get("knowledge_references") or "")[:KNOWLEDGE_CHARS_FOR_CASES]
        design["generation_meta"] = {
            "design_generated_by_llm": by_llm,
            "integrated_matrix_generated_by_llm": by_llm,
            "gap_filled_rows": gap_filled if by_llm else 0,
            "patched_configs": patched["configs"],
            "patched_metrics": patched["metrics"],
            "design_prompt": "test_designer.txt",
            "integrated_prompt": "integrated_matrix_designer.txt（仅补漏）",
        }
        return design

    def post(self, shared, prep_res, exec_res):
        validate_jsonschema(exec_res, TEST_DESIGN_SCHEMA)
        validate_list_of_dict(exec_res.get("objectives", []), TEST_OBJECTIVE_REQUIRED_KEYS, "objectives")
        shared["test_design_spec"] = exec_res
        _trace(shared, "TestDesignNode")
        _emit(shared, "module_result", {"module": "test_design_spec", "data": {
            "objectives": len(exec_res["objectives"]), "rows": len(exec_res["integrated_matrix"])}})
        return "default"


class TestDesignSupervisorNode(Node):
    """设计质量门。确定性修复已在设计节点完成，这里只在仍缺需求覆盖时回流重做。"""

    def prep(self, shared):
        _set_current_node(shared, "TestDesignSupervisorNode")
        return {
            "requirement_spec": shared.get("requirement_spec", {}),
            "test_design_spec": shared.get("test_design_spec", {}),
            "retry_count": int(shared.get("design_retry_count", 0)),
            "max_retries": int(shared.get("design_max_retries", 1)),
        }

    def exec(self, prep_res):
        reqs = prep_res["requirement_spec"].get("final_requirements", [])
        design = prep_res["test_design_spec"]
        rows = design.get("integrated_matrix", []) or []
        issues = []
        if not design.get("objectives"):
            issues.append("objectives为空")
        if not rows:
            issues.append("integrated_matrix为空")
        gaps = design_gaps(rows, reqs, design.get("objectives", []))
        if gaps["missing_reqs"]:
            issues.append(f"整合矩阵缺少需求覆盖: {', '.join(gaps['missing_reqs'])}")
        return {"approved": not issues, "issues": issues, "advice": design.get("design_advice", [])}

    def post(self, shared, prep_res, exec_res):
        _emit(shared, "module_result", {"module": "test_design_supervisor", "data": exec_res})
        for a in exec_res.get("advice") or []:
            _warn(shared, f"设计提示: {a}")
        if exec_res["approved"]:
            shared["design_supervisor_feedback"] = ""
            return "default"
        retry = prep_res["retry_count"] + 1
        shared["design_retry_count"] = retry
        shared["design_supervisor_feedback"] = "；".join(exec_res["issues"])
        _warn(shared, f"设计质量门未通过，第{retry}次回流: {' | '.join(exec_res['issues'])}")
        if retry <= prep_res["max_retries"]:
            return "retry"
        _warn(shared, "设计质量门: 达到最大回流次数，继续后续流程")
        return "default"


# ---------- 测试用例（TCD） ----------

_CELL_KEYS = ("band", "arfcn", "earfcn", "ssb_arfcn", "dl_arfcn", "bandwidth", "bandwidth_mhz", "scs", "scs_khz", "pci",
              "plmn", "tac", "duplex", "tdd", "rsrp", "power", "rs_epre", "cell")
_CORE_KEYS = ("t3", "cause", "apn", "dnn", "psm", "edrx", "drx", "nssai", "ims", "reject", "accept", "auth")
_ENV_IDS = ("AMARISOFT", "PROTOCOL_ANALYZER", "REAL_NETWORK")


def _split_key_configuration(cfg: Dict[str, Any]) -> Dict[str, Any]:
    cell, core, other = {}, {}, {}
    for k, v in (cfg or {}).items():
        lk = str(k).lower()
        if any(x in lk for x in _CELL_KEYS):
            cell[k] = v
        elif any(x in lk for x in _CORE_KEYS):
            core[k] = v
        else:
            other[k] = v
    return {"cells": [{"cell_id": "Cell1", **cell}] if cell else [], "core": core, "ue": {}, **({"other": other} if other else {})}


def fallback_tcd_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 不可用或失败时，从矩阵行规则生成一条最小可用的 TCD。"""
    tp = row.get("test_purpose") or {}
    return {
        "objective_id": row.get("objective_id", ""),
        "title": row.get("scenario", ""),
        "technique": row.get("technique", "normal"),
        "test_purpose": {"with": tp.get("with", ""), "when": tp.get("when") or row.get("scenario", ""),
                         "then": tp.get("then") or "；".join(row.get("pass_criteria") or [])},
        "references": row.get("references") or [],
        "test_environment": row.get("test_environment"),
        "initial_conditions": {"system_simulator": [], "ue": [tp.get("with")] if tp.get("with") else ["UE 开机并完成驻网"],
                               "preamble": []},
        "configuration": _split_key_configuration(row.get("key_configuration") or {}),
        "procedure": [
            {"action": "SETUP", "actor": "TESTER", "params": dict(row.get("key_configuration") or {}),
             "expected": "按配置完成初始条件"},
            {"action": "TRIGGER", "actor": "TESTER", "expected": tp.get("when") or row.get("scenario", "")},
            {"action": "CHECK", "actor": "TESTER", "expected": tp.get("then") or "；".join(row.get("pass_criteria") or []),
             "verdict": True},
        ],
        "pass_fail": row.get("pass_criteria") or [],
        "trace": {"req_ids": [row.get("req_id", "")], "source_refs": [row.get("row_id", "")]},
        "open_points": ["LLM 未生成，需补充信令步骤与消息内容"],
        "tags": ["Fallback"],
    }


def bind_tcds_to_rows(raw: List[Any], rows: List[Dict[str, Any]], reqs: Dict[str, Dict[str, Any]],
                      available: Any = None) -> List[Dict[str, Any]]:
    """把一批 LLM 输出的 TCD 规范化并挂到矩阵行上。

    矩阵行是设计阶段定下来的“合同”：环境、测试技术、追溯关系以行为准，用例只负责把它写细。
    LLM 没写对 row_id 的用例，按 req_id、再按顺序配到还没有用例的行，而不是丢掉或另补一条空壳。
    """
    row_map = {r.get("row_id"): r for r in rows}
    pairs: List[Any] = []
    orphans: List[Any] = []
    for i, tc in enumerate(raw, start=1):
        if not isinstance(tc, dict):
            continue
        norm = normalize_tcd(tc, i)
        refs = [x for x in norm["trace"]["source_refs"] if x in row_map]
        if refs:
            norm["trace"]["source_refs"] = refs
            pairs.append((tc, norm, row_map[refs[0]]))
        else:
            orphans.append((tc, norm))
    uncovered = [r for r in rows if r.get("row_id") not in {x for _, n, _ in pairs for x in n["trace"]["source_refs"]}]
    for tc, norm in orphans:
        ids = set(norm["trace"]["req_ids"])
        row = next((r for r in uncovered if str(r.get("req_id")) in ids), None) or (uncovered[0] if uncovered else None)
        if row is not None:
            uncovered.remove(row)
        else:  # 行都有用例了：多出来的这条挂到同需求的行（一行多条用例是允许的）
            row = next((r for r in rows if str(r.get("req_id")) in ids), rows[0])
        norm["trace"]["source_refs"] = [row["row_id"]]
        pairs.append((tc, norm, row))

    out = []
    for tc, norm, row in pairs:
        rid = str(row.get("req_id") or "")
        if rid and rid not in norm["trace"]["req_ids"]:
            norm["trace"]["req_ids"].insert(0, rid)
        norm["objective_id"] = norm["objective_id"] or row.get("objective_id", "")
        norm["technique"] = row.get("technique") or norm["technique"]
        if not str(tc.get("priority") or "").strip() and reqs.get(rid, {}).get("priority"):
            norm["priority"] = str(reqs[rid]["priority"])
        if not norm["references"]:
            norm["references"] = list(row.get("references") or [])
        row_env = row.get("test_environment") or {}
        norm["test_environment"] = row_env if str(row_env.get("primary")) in _ENV_IDS else envs.normalize_env(
            norm.get("test_environment"), [norm["title"]] + norm["pass_fail"], available)
        out.append(norm)
    return out


class TestCaseBatchGenNode(AsyncNode):
    async def prep_async(self, shared):
        _set_current_node(shared, "TestCaseBatchGenNode",
                          f"第 {int(self.params.get('batch_index', 0)) + 1}/{int(self.params.get('batch_total', 1))} 批")
        design = shared["test_design_spec"]
        reqs = shared["requirement_spec"].get("final_requirements", [])
        return {
            "batch_index": int(self.params.get("batch_index", 0)),
            "batch_total": int(self.params.get("batch_total", 1)),
            "rows": self.params.get("integrated_chunk", []),
            "objectives": design.get("objectives", []),
            "reqs": req_index(reqs),
            "context": {
                "product_profile": (shared.get("product_profile") or {}).get("selected", shared.get("product_profile") or {}),
                "environments": envs.environment_brief(shared.get("test_environments", {})),
                "confirmed_answers": _confirmed_answers(shared),
                "assumptions": shared["requirement_spec"].get("assumptions", []),
                "knowledge_references": design.get("knowledge_references", ""),
                "preferred_actions": shared.get("action_vocabulary") or DEFAULT_ACTION_VOCABULARY,
                "feedback": shared.get("testcase_supervisor_feedback", ""),
            },
            "available": shared.get("test_environments", {}),
        }

    async def exec_async(self, prep_res):
        shared = self._shared
        rows = prep_res["rows"]
        tag = f"TestCaseBatchGenNode-Batch{prep_res['batch_index'] + 1}"
        if not rows:
            return []

        def _not_empty(data: Any):
            if not data.get("testcases"):
                raise ValueError("testcases 不能为空，integrated_matrix 的每一行至少一条用例")

        async def worker(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            obj_ids = {r.get("objective_id") for r in batch}
            req_ids = list(dict.fromkeys(str(r.get("req_id")) for r in batch))
            data = await asyncio.to_thread(
                generate_json,
                shared=shared,
                template_name="test_case_tcd.txt",
                variables={
                    "integrated_matrix_json": json.dumps(batch, ensure_ascii=False),
                    "objectives_json": json.dumps([o for o in prep_res["objectives"] if o.get("objective_id") in obj_ids],
                                                  ensure_ascii=False),
                    "requirements_json": json.dumps([_requirement_view(prep_res["reqs"][r]) for r in req_ids
                                                     if r in prep_res["reqs"]], ensure_ascii=False),
                    "context_json": json.dumps(prep_res["context"], ensure_ascii=False),
                },
                schema=TCD_LIST_SCHEMA,
                warn_tag=tag,
                raise_on_truncate=len(batch) > 1,
                custom_validator=_not_empty,
            )
            return data.get("testcases", [])

        if not shared["llm_client"].enabled:
            _warn(shared, f"{tag}: LLM未配置，按矩阵行规则生成用例")
            raw = [fallback_tcd_from_row(r) for r in rows]
        else:
            try:
                parts = await run_split_on_truncate(rows, worker)
                raw = [tc for part in parts for tc in part]
            except Exception as exc:
                _warn(shared, f"{tag}: 生成失败，该批按矩阵行规则生成: {exc}")
                raw = [fallback_tcd_from_row(r) for r in rows]

        out = bind_tcds_to_rows(raw, rows, prep_res["reqs"], prep_res["available"])
        covered = {r for tc in out for r in tc["trace"]["source_refs"]}
        missing = [r for r in rows if r.get("row_id") not in covered]
        if missing:
            _warn(shared, f"{tag}: {len(missing)} 个矩阵行没有生成用例，已按规则补齐")
            out.extend(bind_tcds_to_rows([fallback_tcd_from_row(r) for r in missing], missing, prep_res["reqs"],
                                         prep_res["available"]))
        return out

    async def post_async(self, shared, prep_res, exec_res):
        shared.setdefault("_testcase_batches", {})[prep_res["batch_index"]] = exec_res
        _emit(shared, "module_result", {"module": "test_case_batch", "data": {
            "batch_index": prep_res["batch_index"] + 1, "batch_total": prep_res["batch_total"], "count": len(exec_res)}})
        return "default"

    async def _run_async(self, shared):
        self._shared = shared
        return await super()._run_async(shared)


class FinalizeTestCaseNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "FinalizeTestCaseNode")
        return {
            "requirements": (shared.get("requirement_spec") or {}).get("final_requirements", []),
            "batches": shared.get("_testcase_batches", {}),
            "retry_rows": shared.get("_retry_rows") or [],
            "previous": (shared.get("test_case_spec") or {}).get("testcases", []),
            "row_order": [r.get("row_id") for r in (shared.get("test_design_spec") or {}).get("integrated_matrix", [])],
        }

    def exec(self, prep_res):
        new: List[Dict[str, Any]] = []
        for idx in sorted(prep_res["batches"].keys()):
            new.extend(prep_res["batches"][idx])
        if prep_res["retry_rows"]:
            keep, _ = split_tcs_by_rows(prep_res["previous"], prep_res["retry_rows"])
            new = keep + new
        tcs = renumber(new, prep_res["row_order"])
        attach_suites(tcs, req_index(prep_res["requirements"]))
        return {"testcases": tcs}

    def post(self, shared, prep_res, exec_res):
        validate_list_of_dict(exec_res["testcases"], TESTCASE_REQUIRED_KEYS, "testcases")
        shared["test_case_spec"] = exec_res
        shared["_retry_rows"] = []
        _trace(shared, "FinalizeTestCaseNode")
        _emit(shared, "module_result", {"module": "test_case_spec", "data": {"count": len(exec_res["testcases"])}})
        return "default"


TC_REVIEW_SCHEMA = {
    "type": "object",
    "required": ["reviews"],
    "properties": {"reviews": {"type": "array", "items": {
        "type": "object", "required": ["tc_id"],
        "properties": {"tc_id": {"type": "string"}, "verdict": {"type": "string"},
                       "issues": {"type": "array", "items": {"type": "object"}}}}}},
}
REVIEW_BATCH_SIZE = 5


class TestCaseSupervisorNode(AsyncNode):
    """用例质量门。

    1) 确定性：补入需求写明的配置和数值门限，检查结构；
    2) LLM 专家评审（首轮、可关）：另起一次调用，以评审者视角检查协议正确性、TP 是否可判定、与需求是否一致；
    3) 有问题的用例只返工其矩阵行，问题逐条写进反馈；评审的一般性意见留在用例的 review_notes 里。
    """

    async def prep_async(self, shared):
        _set_current_node(shared, "TestCaseSupervisorNode")
        retry_count = int(shared.get("testcase_retry_count", 0))
        llm_enabled = bool(getattr(shared.get("llm_client"), "enabled", False))
        return {
            "reqs": shared.get("requirement_spec", {}).get("final_requirements", []),
            "rows": (shared.get("test_design_spec") or {}).get("integrated_matrix", []),
            "tcs": shared.get("test_case_spec", {}).get("testcases", []),
            "retry_count": retry_count,
            "max_retries": int(shared.get("testcase_max_retries", 1)),
            "llm_enabled": llm_enabled,
            # 评审只做一轮：返工后的用例不再评审，避免来回拉扯和成本失控
            "expert_review": llm_enabled and retry_count == 0 and shared.get("expert_review", True) is not False,
        }

    async def _expert_review(self, prep_res) -> List[Dict[str, Any]]:
        shared = self._shared
        reqs = req_index(prep_res["reqs"])
        row_map = {r.get("row_id"): r for r in prep_res["rows"]}
        tcs = [tc for tc in prep_res["tcs"] if "Fallback" not in (tc.get("tags") or [])]
        batches = [tcs[i:i + REVIEW_BATCH_SIZE] for i in range(0, len(tcs), REVIEW_BATCH_SIZE)]

        async def one(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            rids = list(dict.fromkeys(str(r) for tc in batch for r in tc["trace"]["req_ids"]))
            view = []
            for tc in batch:
                item = {k: v for k, v in summarize_for_prompt(tc).items() if k not in ("requirement_configs", "observability")}
                row = next((row_map[r] for r in tc["trace"]["source_refs"] if r in row_map), None)
                if row:
                    item["matrix_row"] = {k: row.get(k) for k in ("row_id", "technique", "scenario", "test_purpose", "pass_criteria")}
                view.append(item)
            data = await asyncio.to_thread(
                generate_json,
                shared=shared,
                template_name="test_case_reviewer.txt",
                variables={
                    "testcases_json": json.dumps(view, ensure_ascii=False),
                    "requirements_json": json.dumps([_requirement_view(reqs[r]) for r in rids if r in reqs], ensure_ascii=False),
                    "environments_json": json.dumps(envs.environment_brief(shared.get("test_environments", {})), ensure_ascii=False),
                },
                schema=TC_REVIEW_SCHEMA,
                warn_tag="TestCaseReviewer",
                max_retries=1,
            )
            return [r for r in data.get("reviews", []) if isinstance(r, dict)]

        results = await asyncio.gather(*(one(b) for b in batches), return_exceptions=True)
        failed = [r for r in results if isinstance(r, Exception)]
        if failed:  # 评审是增强项，失败不影响出用例
            _warn(shared, f"专家评审: {len(failed)}/{len(batches)} 批评审调用失败，已跳过: {failed[0]}")
        return [rv for r in results if not isinstance(r, Exception) for rv in r]

    async def exec_async(self, prep_res):
        tcs = prep_res["tcs"]
        res = review_testcases(tcs, prep_res["reqs"], prep_res["rows"])
        coverage_issues = res["issues"][len(res["per_tc"]):]
        res["expert"] = {"major": 0, "minor": 0, "reviewed": False}
        if prep_res["expert_review"] and tcs:
            _set_current_node(self._shared, "TestCaseSupervisorNode", "专家评审")
            reviews = await self._expert_review(prep_res)
            res["expert"] = {**merge_expert_review(res["per_tc"], tcs, reviews), "reviewed": True}
        valid_rows = {r.get("row_id") for r in prep_res["rows"]}
        retry_rows = rows_for_tcs(res["per_tc"], tcs, valid_rows)
        for rid in res["missing_reqs"]:
            retry_rows.extend(r["row_id"] for r in prep_res["rows"] if str(r.get("req_id")) == rid and r["row_id"] not in retry_rows)
        res["retry_rows"] = retry_rows
        res["issues"] = [f"{k}: {'；'.join(v)}" for k, v in res["per_tc"].items()] + coverage_issues
        return res

    async def post_async(self, shared, prep_res, exec_res):
        _emit(shared, "module_result", {"module": "test_case_supervisor", "data": {
            "issues": exec_res["issues"][:20], "patched": exec_res["patched"], "retry_rows": exec_res["retry_rows"],
            "expert": exec_res["expert"]}})
        if exec_res["expert"]["reviewed"]:
            _warn(shared, f"专家评审: 发现 {exec_res['expert']['major']} 个需要返工的问题、{exec_res['expert']['minor']} 条一般意见（见各用例的评审意见）")
        retry = prep_res["retry_count"] + 1
        if exec_res["retry_rows"] and prep_res["llm_enabled"] and retry <= prep_res["max_retries"]:
            shared["testcase_retry_count"] = retry
            shared["_retry_rows"] = exec_res["retry_rows"]
            shared["testcase_supervisor_feedback"] = feedback_for_rows(exec_res["per_tc"], prep_res["tcs"], exec_res["retry_rows"])
            _warn(shared, f"用例质量门: {len(exec_res['retry_rows'])} 个测试点的用例需要改进，只返工这些（第{retry}次）")
            return "retry"
        # 确定性修复的统计只在收尾这一轮报（返工的用例会重新核对，之前的数字已经不作数）
        final = review_stats(prep_res["tcs"])
        if final["patched"]:
            _warn(shared, f"用例质量门: {final['patched']} 项需求写明的配置未出现在用例中，已按需求原值补入（requirement_configs 标为 patched）")
        if exec_res["criteria_added"]:
            _warn(shared, f"用例质量门: {exec_res['criteria_added']} 条带数值门限的通过标准未进用例，已按测试点原文补入 pass_fail")
        if final["conflict"]:
            _warn(shared, f"用例质量门: {final['conflict']} 项需求配置与用例取值不一致，需求值已另存并写入 open_points，请人工确认")
        if exec_res["metrics_missing"]:
            _warn(shared, f"用例质量门: 以下需求数值门限未出现在用例通过标准中: {'；'.join(exec_res['metrics_missing'][:6])}")
        for line in exec_res["issues"][:10]:
            _warn(shared, f"用例质量门: {line}")
        shared["testcase_supervisor_feedback"] = ""
        return "default"

    async def _run_async(self, shared):
        self._shared = shared
        return await super()._run_async(shared)


class AssembleResultNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "AssembleResultNode")
        return shared

    def exec(self, prep_res):
        req_spec = prep_res.get("requirement_spec", {})
        design = prep_res.get("test_design_spec", {})
        case_spec = prep_res.get("test_case_spec", {})
        executable_cases = prep_res.get("executable_cases", {})
        persona_reviews = prep_res.get("persona_reviews", {})
        questions = req_spec.get("questions_to_ask", [])
        assumptions = req_spec.get("assumptions", [])
        req_lines = ["# 测试需求稿", "## 需求清单与来源"]
        for r in req_spec.get("final_requirements", []):
            req_lines.append(
                f"- {r.get('req_id','')} | {r.get('title','')} | persona_sources={','.join(r.get('persona_sources', []))}"
            )
        if questions:
            req_lines.append("## 待澄清问题")
            req_lines.extend([f"- {q}" for q in questions])
        if assumptions:
            req_lines.append("## 当前默认假设")
            req_lines.extend([f"- {a}" for a in assumptions])
        return {
            "pipeline": [
                "Requirement Intake",
                "Req Parse & Normalize",
                "Tri-Persona Review",
                "Synthesis & Decision",
                "Test Design (TP + technique matrix)",
                "Design Quality Gate",
                "Test Case Description (3GPP TCD)",
                "Test Case Quality Gate + Expert Review",
                "Executable Case Export",
            ],
            "input": {
                "requirements": [r.get("title", "") for r in req_spec.get("final_requirements", [])],
                "rag_context_provided": bool(prep_res.get("rag_context")),
                "framework_capability_catalog_provided": bool(prep_res.get("framework_capability_catalog")),
            },
            "missing_inputs": prep_res.get("missing_inputs", []),
            "warnings": prep_res.get("warnings", []),
            "artifacts_structured": {
                "requirement_spec": req_spec,
                "persona_reviews": persona_reviews,
                "test_design_spec": design,
                "test_case_spec": case_spec,
                "executable_cases": executable_cases,
            },
            "artifacts": {
                "test_requirements": "\n".join(req_lines),
                "review_process": json.dumps(persona_reviews, ensure_ascii=False, indent=2),
                "test_design": json.dumps(design, ensure_ascii=False, indent=2),
                "test_cases": json.dumps(case_spec, ensure_ascii=False, indent=2),
                "executable_cases": json.dumps(executable_cases, ensure_ascii=False, indent=2),
            },
            "trace": prep_res.get("trace", []),
            "llm_usage": prep_res.get("llm_usage", {}),
        }

    def post(self, shared, prep_res, exec_res):
        shared["final_result"] = exec_res
        _trace(shared, "AssembleResultNode")
        _emit(shared, "final_result", exec_res)
        return None
