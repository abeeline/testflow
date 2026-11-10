"""PocketFlow 节点：只做编排，具体规则在 core/ 下。

流水线（与 3GPP 测试设计过程对应）：
    需求解析 → 三方评审 → 综合定稿           （测试需求分析，HITL 多轮）
    → 测试设计：测试目标 + 按测试技术导出的整合矩阵（每行一个测试点，带 TP）
    → 设计质量门：确定性补入需求配置/数值门限，缺覆盖时只为缺口补行
    → 测试用例：每个测试点写成 3GPP 风格测试用例描述（TCD），分批并行，输出过长自动拆批
    → 用例质量门：补入需求配置，只返工结构不合格的用例
    → 可执行用例（exec_cases.py）：由 TCD 投影草稿，LLM 做平台适配
"""
import asyncio
import datetime as dt
import json
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
from core.llm import generate_json, run_split_on_truncate
from core.quality import (
    design_advice,
    design_gaps,
    feedback_for_rows,
    repair_design_rows,
    req_index,
    req_metrics,
    review_testcases,
    split_tcs_by_rows,
)
from core.tcd import TCD_LIST_SCHEMA, TECHNIQUES, normalize_tcd, renumber
from utils.agent_runner import run_json_agent_with_retry
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
    "TestCaseSupervisorNode": "用例质量门",
    "ExecutableCaseNode": "生成可执行用例",
    "AssembleResultNode": "汇总结果",
}
KNOWLEDGE_CHARS_FOR_CASES = 6000


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _trace(shared: Dict[str, Any], node: str):
    shared.setdefault("trace", []).append({"node": node, "time": _now()})


def _emit(shared: Dict[str, Any], event_type: str, payload: Dict[str, Any]):
    q = shared.get("event_queue")
    if not q:
        return
    try:
        q.put_nowait({"type": event_type, "payload": payload})
    except Exception:
        pass


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


class IntakeNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "IntakeNode")
        return {
            "requirements": shared.get("input_requirements", []),
            "rag_context": shared.get("rag_context", ""),
            "review_feedback": shared.get("review_feedback", ""),
            "framework_capability_catalog": shared.get("framework_capability_catalog", ""),
            "product_profile": shared.get("product_profile", {}),
            "action_vocabulary": shared.get("action_vocabulary") or DEFAULT_ACTION_VOCABULARY,
            "assertion_vocabulary": shared.get("assertion_vocabulary") or DEFAULT_ASSERTION_VOCABULARY,
            "capabilities": shared.get("capabilities") or DEFAULT_CAPABILITIES,
        }

    def exec(self, prep_res):
        requirements = [x.strip() for x in prep_res["requirements"] if x and x.strip()]
        if not requirements:
            raise ValueError("requirements不能为空")

        items = []
        for idx, text in enumerate(requirements, start=1):
            items.append(
                {
                    "req_id": f"REQ-{idx:03d}",
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
            "rag_context": prep_res["rag_context"].strip(),
            "review_feedback": prep_res["review_feedback"].strip(),
            "framework_capability_catalog": prep_res["framework_capability_catalog"].strip(),
            "product_profile": prep_res.get("product_profile") or {},
            "action_vocabulary": prep_res["action_vocabulary"],
            "assertion_vocabulary": prep_res["assertion_vocabulary"],
            "capabilities": prep_res["capabilities"],
        }

    def post(self, shared, prep_res, exec_res):
        shared.update(exec_res)
        missing_inputs = []
        if not exec_res["rag_context"]:
            missing_inputs.append("缺少RAG文档上下文（3GPP/运营商/历史缺陷等）")
        if not exec_res["framework_capability_catalog"]:
            missing_inputs.append("缺少测试脚本框架能力清单（驱动、日志采集、报告能力）")
        shared["missing_inputs"] = missing_inputs
        _trace(shared, "IntakeNode")
        return "default"


class ReqParseNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "ReqParseNode")
        return {
            "seed_requirements": shared["seed_requirements"],
            "rag_context": shared.get("rag_context", ""),
            "review_feedback": shared.get("review_feedback", ""),
            "product_profile": shared.get("product_profile", {}),
        }

    def exec(self, prep_res):
        fallback = prep_res["seed_requirements"]
        return run_json_agent_with_retry(
            shared=self._shared,
            template_name="req_parse.txt",
            variables={
                "glossary_json": json.dumps({"attach": "注册", "idle reselection": "驻留重选"}, ensure_ascii=False),
                "doc_meta_json": json.dumps({"type": "USER_INPUT", "lang": "mixed"}, ensure_ascii=False),
                "text_chunk": json.dumps(prep_res["seed_requirements"], ensure_ascii=False),
                "rag_context": prep_res.get("rag_context", ""),
                "review_feedback": prep_res.get("review_feedback", ""),
                "product_profile_json": json.dumps(prep_res.get("product_profile", {}), ensure_ascii=False),
                "output_schema": json.dumps(REQUIREMENT_LIST_SCHEMA, ensure_ascii=False),
            },
            schema=REQUIREMENT_LIST_SCHEMA,
            fallback=fallback,
            warn_tag="ReqParseNode",
        )

    def _run(self, shared):
        self._shared = shared
        return super()._run(shared)

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

    async def _review_persona(self, shared: Dict[str, Any], template: str, role: str, requirements: List[Dict[str, Any]]):
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
            run_json_agent_with_retry,
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
            warn_tag=f"TriPersonaReviewNode-{role}",
        )

    async def exec_async(self, prep_res):
        reqs = prep_res["requirements"]
        shared = self._shared
        spec_task = self._review_persona(shared, "review_spec_lawyer.txt", "SpecLawyer", reqs)
        carrier_task = self._review_persona(shared, "review_carrier.txt", "CarrierReviewer", reqs)
        ux_task = self._review_persona(shared, "review_ux_advocate.txt", "UXAdvocate", reqs)
        spec, carrier, ux = await asyncio.gather(spec_task, carrier_task, ux_task)
        return {"spec": spec, "carrier": carrier, "ux": ux}

    def _run(self, shared):
        raise RuntimeError("Use AsyncFlow.run_async for TriPersonaReviewNode")

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


class SynthesisNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "SynthesisNode")
        return {"requirements": shared["requirements_parsed"], "reviews": shared["persona_reviews"]}

    def exec(self, prep_res):
        fallback = {
            "final_requirements": prep_res["requirements"],
            "conflicts": [],
            "questions_to_ask": ["请确认每条需求的量化通过标准"],
            "assumptions": ["默认按P1执行，待业务确认后升降级"],
        }
        return run_json_agent_with_retry(
            shared=self._shared,
            template_name="synthesis_arbiter.txt",
            variables={
                "requirements_json": json.dumps(prep_res["requirements"], ensure_ascii=False),
                "reviews_spec_json": json.dumps(prep_res["reviews"]["spec"], ensure_ascii=False),
                "reviews_carrier_json": json.dumps(prep_res["reviews"]["carrier"], ensure_ascii=False),
                "reviews_ux_json": json.dumps(prep_res["reviews"]["ux"], ensure_ascii=False),
                "return_schema": json.dumps(SYNTHESIS_SCHEMA, ensure_ascii=False),
                "output_schema": json.dumps(SYNTHESIS_SCHEMA, ensure_ascii=False),
            },
            schema=SYNTHESIS_SCHEMA,
            fallback=fallback,
            warn_tag="SynthesisNode",
        )

    def _run(self, shared):
        self._shared = shared
        return super()._run(shared)

    def post(self, shared, prep_res, exec_res):
        validate_jsonschema(exec_res, SYNTHESIS_SCHEMA)
        restored = restore_explicit_configs(exec_res.get("final_requirements", []), prep_res["requirements"])
        if restored:
            shared.setdefault("warnings", []).append(
                f"SynthesisNode: 综合评审丢失了 {restored} 项需求显式配置，已按 req_id 补回。")
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
        crit = crit if isinstance(crit, list) else [str(crit)]
        technique = str(r.get("technique") or "normal").lower()
        norm.append({
            "row_id": r.get("row_id") or f"ROW-{idx:03d}",
            "req_id": r.get("req_id") or ((obj.get("linked_reqs") or [f"REQ-{idx:03d}"])[0]),
            "objective_id": r.get("objective_id") or f"TO-{idx:03d}",
            "technique": technique if technique in TECHNIQUES else "normal",
            "scenario": scenario,
            "test_purpose": _norm_purpose(r.get("test_purpose"), scenario),
            "key_configuration": cfg,
            "pass_criteria": crit or ["关键指标满足需求标准"],
            "references": [str(x) for x in (r.get("references") or []) if str(x).strip()],
            "test_environment": envs.normalize_env(r.get("test_environment"), [scenario] + crit, available_envs),
        })
    # row_id 去重
    seen = set()
    for n, row in enumerate(norm, start=start_index):
        while row["row_id"] in seen:
            row["row_id"] = f"ROW-{n:03d}-{len(seen)}"
        seen.add(row["row_id"])
    return norm


def _fallback_rows(missing_reqs: List[str], missing_objs: List[str], final_requirements: List[Dict[str, Any]],
                   objectives: List[Dict[str, Any]], available_envs: Any, start: int) -> List[Dict[str, Any]]:
    """补漏调用也失败时的规则兜底：每个缺口一行正常流程，保证追溯完整。"""
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
            oid = f"TO-GAP-{len(objectives) + 1:02d}"
            req = reqs.get(rid, {})
            objectives.append({"objective_id": oid, "linked_reqs": [rid], "goal": req.get("title", rid),
                               "success_criteria": req_metrics(req) or ["主流程成功"], "evidence": ["modem_log"],
                               "priority": req.get("priority", "P1"), "risk_notes": "规则补全的目标"})
        rows.append((rid, oid, reqs.get(rid, {}).get("title", "")))
    out = []
    for i, (rid, oid, goal) in enumerate(rows, start=start):
        req = reqs.get(rid, {})
        out.append({"row_id": f"ROW-{i:03d}", "req_id": rid, "objective_id": oid, "technique": "normal",
                    "scenario": goal or rid, "test_purpose": {"with": "", "when": "", "then": goal},
                    "key_configuration": {}, "pass_criteria": req_metrics(req) or ["关键指标满足需求标准"],
                    "references": [], "test_environment": envs.recommend([goal], available_envs)})
    return out


class TestDesignNode(Node):
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

    def exec(self, prep_res):
        shared = self._shared
        reqs = prep_res["final_requirements"]
        available = prep_res.get("test_environments", {})

        def _custom(data: Any):
            if not isinstance(data.get("objectives"), list) or not data["objectives"]:
                raise ValueError("objectives 不能为空")
            if not isinstance(data.get("integrated_matrix"), list) or not data["integrated_matrix"]:
                raise ValueError("integrated_matrix 不能为空，每个目标至少一行")

        data = generate_json(
            shared=shared,
            template_name="test_designer.txt",
            variables={
                "final_requirements_json": json.dumps(reqs, ensure_ascii=False),
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
            warn_tag="TestDesignNode",
            custom_validator=_custom,
        )
        design = _normalize_objectives(data, reqs)
        objectives = design["objectives"]
        rows = _normalize_integrated_rows(data.get("integrated_matrix", []), reqs, objectives, available)

        gaps = design_gaps(rows, reqs, objectives)
        gap_filled = 0
        if gaps["missing_reqs"] or gaps["missing_objectives"]:
            _set_current_node(shared, "TestDesignNode", "为未覆盖的需求补充测试点")
            start = len(rows) + 1
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
                        "next_row_id": f"ROW-{start:03d}",
                    },
                    schema=INTEGRATED_MATRIX_SCHEMA,
                    warn_tag="IntegratedMatrixGapFill",
                )
                new_rows = _normalize_integrated_rows(extra.get("integrated_matrix", []), reqs, objectives, available, start)
            except Exception as exc:
                _warn(shared, f"TestDesignNode: 补漏生成失败，按规则补行: {exc}")
                new_rows = []
            rows.extend(new_rows)
            gap_filled = len(new_rows)
            gaps = design_gaps(rows, reqs, objectives)
            if gaps["missing_reqs"] or gaps["missing_objectives"]:
                fb = _fallback_rows(gaps["missing_reqs"], gaps["missing_objectives"], reqs, objectives, available, len(rows) + 1)
                rows.extend(fb)
                gap_filled += len(fb)
        seen = set()
        for row in rows:  # 补漏行可能和已有行撞号
            while row["row_id"] in seen:
                row["row_id"] = row["row_id"] + "b"
            seen.add(row["row_id"])

        patched = repair_design_rows(rows, reqs)
        if patched["configs"]:
            _warn(shared, f"设计质量门: {patched['configs']} 项需求写明的配置未进矩阵，已按需求原值补入 key_configuration")
        design["integrated_matrix"] = rows
        design["design_advice"] = design_advice(rows, reqs)
        design["knowledge_references"] = str(prep_res.get("knowledge_references") or "")[:KNOWLEDGE_CHARS_FOR_CASES]
        design["generation_meta"] = {
            "design_generated_by_llm": True,
            "integrated_matrix_generated_by_llm": True,
            "gap_filled_rows": gap_filled,
            "patched_configs": patched["configs"],
            "patched_metrics": patched["metrics"],
            "design_prompt": "test_designer.txt",
            "integrated_prompt": "integrated_matrix_designer.txt（仅补漏）",
        }
        return design

    def _run(self, shared):
        self._shared = shared
        return super()._run(shared)

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

        async def worker(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            obj_ids = {r.get("objective_id") for r in batch}
            req_ids = {str(r.get("req_id")) for r in batch}
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
                custom_validator=lambda d: None if d.get("testcases") else (_ for _ in ()).throw(ValueError("testcases 不能为空")),
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

        row_map = {r.get("row_id"): r for r in rows}
        out = []
        for i, tc in enumerate(raw, start=1):
            if not isinstance(tc, dict):
                continue
            norm = normalize_tcd(tc, i)
            refs = [x for x in norm["trace"]["source_refs"] if x in row_map]
            row = row_map.get(refs[0]) if refs else None
            if row is None and len(rows) == 1:
                row = rows[0]
                norm["trace"]["source_refs"] = [row["row_id"]]
            if row:
                if not norm["trace"]["req_ids"]:
                    norm["trace"]["req_ids"] = [row.get("req_id", "")]
                norm["objective_id"] = norm["objective_id"] if norm["objective_id"] != "TO-001" else row.get("objective_id", "TO-001")
                if not norm.get("references"):
                    norm["references"] = row.get("references") or []
            norm["test_environment"] = envs.normalize_env(
                norm.get("test_environment"), [norm["title"]] + norm["pass_fail"], prep_res["available"],
                linked=(row or {}).get("test_environment"))
            if row and str((row.get("test_environment") or {}).get("primary")) in ("AMARISOFT", "PROTOCOL_ANALYZER", "REAL_NETWORK"):
                norm["test_environment"] = row["test_environment"]  # 环境由设计决定，用例不改
            out.append(norm)
        covered = {r for tc in out for r in tc["trace"]["source_refs"]}
        missing = [r for r in rows if r.get("row_id") not in covered]
        if missing:
            _warn(shared, f"{tag}: {len(missing)} 个矩阵行没有生成用例，已按规则补齐")
            out.extend(normalize_tcd(fallback_tcd_from_row(r), len(out) + 1) for r in missing)
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
        return {"testcases": renumber(new, prep_res["row_order"])}

    def post(self, shared, prep_res, exec_res):
        validate_list_of_dict(exec_res["testcases"], TESTCASE_REQUIRED_KEYS, "testcases")
        shared["test_case_spec"] = exec_res
        shared["_retry_rows"] = []
        _trace(shared, "FinalizeTestCaseNode")
        _emit(shared, "module_result", {"module": "test_case_spec", "data": {"count": len(exec_res["testcases"])}})
        return "default"


class TestCaseSupervisorNode(Node):
    """用例质量门：补入需求配置；结构不合格的用例只返工其矩阵行。"""

    def prep(self, shared):
        _set_current_node(shared, "TestCaseSupervisorNode")
        return {
            "reqs": shared.get("requirement_spec", {}).get("final_requirements", []),
            "rows": (shared.get("test_design_spec") or {}).get("integrated_matrix", []),
            "tcs": shared.get("test_case_spec", {}).get("testcases", []),
            "retry_count": int(shared.get("testcase_retry_count", 0)),
            "max_retries": int(shared.get("testcase_max_retries", 1)),
            "llm_enabled": bool(getattr(shared.get("llm_client"), "enabled", False)),
        }

    def exec(self, prep_res):
        res = review_testcases(prep_res["tcs"], prep_res["reqs"])
        retry_rows = list(res["retry_rows"])
        for rid in res["missing_reqs"]:
            retry_rows.extend(r["row_id"] for r in prep_res["rows"] if str(r.get("req_id")) == rid and r["row_id"] not in retry_rows)
        res["retry_rows"] = retry_rows
        return res

    def post(self, shared, prep_res, exec_res):
        _emit(shared, "module_result", {"module": "test_case_supervisor", "data": {
            "issues": exec_res["issues"][:20], "patched": exec_res["patched"], "retry_rows": exec_res["retry_rows"]}})
        if exec_res["patched"]:
            _warn(shared, f"用例质量门: {exec_res['patched']} 项需求写明的配置未出现在用例中，已按需求原值补入（requirement_configs 标为 patched）")
        if exec_res["metrics_missing"]:
            _warn(shared, f"用例质量门: 以下需求数值门限未出现在用例通过标准中: {'；'.join(exec_res['metrics_missing'][:6])}")
        retry = prep_res["retry_count"] + 1
        if exec_res["retry_rows"] and prep_res["llm_enabled"] and retry <= prep_res["max_retries"]:
            shared["testcase_retry_count"] = retry
            shared["_retry_rows"] = exec_res["retry_rows"]
            shared["testcase_supervisor_feedback"] = feedback_for_rows(exec_res["per_tc"], prep_res["tcs"], exec_res["retry_rows"])
            _warn(shared, f"用例质量门: {len(exec_res['retry_rows'])} 个测试点的用例不合格，只返工这些（第{retry}次）")
            return "retry"
        for line in exec_res["issues"][:10]:
            _warn(shared, f"用例质量门: {line}")
        shared["testcase_supervisor_feedback"] = ""
        return "default"


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
                "Test Case Quality Gate",
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
