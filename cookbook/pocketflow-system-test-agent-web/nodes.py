import asyncio
import datetime as dt
import json
from typing import Any, Dict, List

from pocketflow import AsyncNode, Node
from schemas import (
    DEFAULT_ACTION_VOCABULARY,
    DEFAULT_ASSERTION_VOCABULARY,
    DEFAULT_CAPABILITIES,
    PERSONA_REVIEW_SCHEMA,
    REQUIREMENT_ITEM_SCHEMA,
    REQUIREMENT_LIST_SCHEMA,
    SCRIPT_PLAN_SCHEMA,
    SCRIPTSPEC_REQUIRED_KEYS,
    SYNTHESIS_SCHEMA,
    TESTCASE_REQUIRED_KEYS,
    TESTCASE_SCHEMA,
    TEST_DESIGN_SCHEMA,
    TEST_OBJECTIVE_REQUIRED_KEYS,
    INTEGRATED_MATRIX_SCHEMA,
)
from utils.agent_runner import run_json_agent_strict_with_retry, run_json_agent_with_retry, run_text_agent
from utils.schema_validation import ensure_actions_in_vocabulary, validate_jsonschema, validate_list_of_dict


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _trace(shared: Dict[str, Any], node: str):
    shared.setdefault("trace", []).append({"node": node, "time": _now()})

def _set_current_node(shared: Dict[str, Any], node: str):
    shared["current_node"] = node
    _emit(shared, "node_running", {"node": node})


def _emit(shared: Dict[str, Any], event_type: str, payload: Dict[str, Any]):
    q = shared.get("event_queue")
    if not q:
        return
    try:
        q.put_nowait({"type": event_type, "payload": payload})
    except Exception:
        pass


def _fallback_testcases_from_objectives(objectives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for idx, obj in enumerate(objectives, start=1):
        cases.append(
            {
                "tc_id": f"TC-{idx:03d}",
                "objective_id": obj.get("objective_id", f"TO-{idx:03d}"),
                "title": obj.get("goal", f"测试目标-{idx}"),
                "tags": ["Regression", obj.get("priority", "P1")],
                "preconditions": ["网络与SIM配置正确"],
                "steps": [
                    {"action": "SET_DEVICE_STATE", "params": {"airplane": False}},
                    {"action": "TRIGGER_REGISTRATION", "params": {"mode": "NR_SA"}},
                    {"action": "WAIT", "params": {"timeout_s": 60}},
                    {"action": "CHECK", "params": {"item": "IMS_REGISTERED"}},
                    {"action": "COLLECT_LOG", "params": {"items": ["modem_log", "logcat"]}},
                ],
                "expected": obj.get("success_criteria", []),
                "pass_fail": ["满足目标成功标准", "失败可定位"],
                "observability": {
                    "must_capture": obj.get("evidence", ["modem_log", "logcat"]),
                    "assertions": ["ASSERT_IMS_REGISTERED"],
                },
                "failure_taxonomy": [
                    {"code": "TC_FAIL", "signals": ["timeout"], "likely_owner": "MODEM_OR_NETWORK"}
                ],
                "trace": {"req_ids": obj.get("linked_reqs", []), "source_refs": ["USER_INPUT"]},
            }
        )
    return cases


def _normalize_objectives(data: Dict[str, Any], final_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
    objectives = data.get("objectives", [])
    req_ids = [r.get("req_id") for r in final_requirements if isinstance(r, dict) and r.get("req_id")]
    norm = []
    for idx, obj in enumerate(objectives, start=1):
        if not isinstance(obj, dict):
            continue
        linked = obj.get("linked_reqs") or obj.get("req_ids") or req_ids[:1] or [f"REQ-{idx:03d}"]
        evidence = obj.get("evidence") or obj.get("must_capture") or ["modem_log", "logcat"]
        if isinstance(evidence, dict):
            evidence = evidence.get("must_capture", []) or ["modem_log", "logcat"]
        norm.append(
            {
                "objective_id": obj.get("objective_id") or obj.get("objectiveId") or obj.get("id") or f"TO-{idx:03d}",
                "linked_reqs": linked,
                "goal": obj.get("goal") or obj.get("title") or obj.get("objective") or f"测试目标-{idx}",
                "success_criteria": obj.get("success_criteria") or obj.get("pass_fail") or ["主流程成功"],
                "evidence": evidence,
                "priority": obj.get("priority") or "P1",
                "risk_notes": obj.get("risk_notes") or obj.get("risk") or "待补充",
            }
        )
    data["objectives"] = norm
    cms = data.get("coverage_matrices", [])
    norm_cms = []
    for idx, cm in enumerate(cms if isinstance(cms, list) else [], start=1):
        if not isinstance(cm, dict):
            continue
        dims = cm.get("dimensions", [])
        if isinstance(dims, dict):
            dims = [{"name": k, "values": v if isinstance(v, list) else [v]} for k, v in dims.items()]
        if not isinstance(dims, list):
            dims = []
        norm_cms.append(
            {
                "matrix_id": cm.get("matrix_id") or cm.get("matrixId") or f"CM-{idx:03d}",
                "dimensions": dims,
                "sampling_strategy": cm.get("sampling_strategy") or cm.get("sampling") or {"type": "pairwise"},
            }
        )
    data["coverage_matrices"] = norm_cms
    data.setdefault("design_notes", [])
    data.setdefault("de_scoped", [])
    return data


def _default_objectives_from_requirements(final_requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    req_ids = [r.get("req_id") for r in final_requirements if isinstance(r, dict) and r.get("req_id")]
    out = []
    for idx, r in enumerate(final_requirements, start=1):
        out.append(
            {
                "objective_id": f"TO-{idx:03d}",
                "linked_reqs": [r.get("req_id")] if r.get("req_id") else (req_ids[:1] or [f"REQ-{idx:03d}"]),
                "goal": r.get("title", f"测试目标-{idx}"),
                "success_criteria": r.get("acceptance", {}).get("pass_fail", []) or ["主流程成功", "异常可恢复"],
                "evidence": r.get("observability", {}).get("must_capture", []) or ["modem_log", "logcat"],
                "priority": r.get("priority", "P1"),
                "risk_notes": "由需求自动补全目标",
            }
        )
    return out


def _extract_req_metrics(req: Dict[str, Any]) -> List[str]:
    acc = req.get("acceptance", {}) if isinstance(req, dict) else {}
    metrics = []
    metrics.extend(acc.get("pass_fail", []) if isinstance(acc.get("pass_fail", []), list) else [])
    metrics.extend(acc.get("kpi", []) if isinstance(acc.get("kpi", []), list) else [])
    return [str(x) for x in metrics if str(x).strip()]


def _first_dimension_values(coverage_matrices: List[Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for cm in coverage_matrices:
        for d in cm.get("dimensions", []):
            if not isinstance(d, dict):
                continue
            name = d.get("name")
            vals = d.get("values", [])
            if name and isinstance(vals, list) and vals:
                out[name] = str(vals[0])
    return out


def _fallback_integrated_matrix(
    final_requirements: List[Dict[str, Any]],
    objectives: List[Dict[str, Any]],
    coverage_matrices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    req_map = {r.get("req_id"): r for r in final_requirements if isinstance(r, dict) and r.get("req_id")}
    dim_defaults = _first_dimension_values(coverage_matrices)
    rows = []
    for idx, obj in enumerate(objectives, start=1):
        req_id = (obj.get("linked_reqs") or [None])[0]
        req = req_map.get(req_id, {})
        cfg = {
            "RAT": dim_defaults.get("RAT_MODE", "NR_SA"),
            "Mobility": dim_defaults.get("MOBILITY", "CONN_HO"),
            "SignalOrPower": dim_defaults.get("POWER", "NORMAL"),
            "Concurrency": dim_defaults.get("CONCURRENCY", "DATA_ONLY"),
            "Operator": dim_defaults.get("OPERATOR_PROFILE", "GENERIC"),
        }
        scenario = f"{obj.get('goal','目标验证')} | {cfg['RAT']} / {cfg['Mobility']} / {cfg['SignalOrPower']}"
        pass_criteria = _extract_req_metrics(req) or obj.get("success_criteria", []) or ["关键指标满足需求标准"]
        rows.append(
            {
                "row_id": f"ROW-{idx:03d}",
                "req_id": req_id or f"REQ-{idx:03d}",
                "objective_id": obj.get("objective_id", f"TO-{idx:03d}"),
                "scenario": scenario,
                "key_configuration": cfg,
                "pass_criteria": pass_criteria,
            }
        )
    return rows


def _normalize_integrated_rows(
    rows: List[Dict[str, Any]],
    final_requirements: List[Dict[str, Any]],
    objectives: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    req_map = {r.get("req_id"): r for r in final_requirements if isinstance(r, dict) and r.get("req_id")}
    obj_map = {o.get("objective_id"): o for o in objectives if isinstance(o, dict) and o.get("objective_id")}
    norm = []
    for idx, r in enumerate(rows, start=1):
        if not isinstance(r, dict):
            continue
        req_id = r.get("req_id")
        obj_id = r.get("objective_id")
        req = req_map.get(req_id, {})
        obj = obj_map.get(obj_id, {})
        cfg = r.get("key_configuration", {})
        if not isinstance(cfg, dict):
            cfg = {}
        scenario = str(r.get("scenario") or "").strip()
        if not scenario:
            scenario = f"{obj.get('goal','目标验证')} @ {cfg.get('RAT','NR_SA')}/{cfg.get('Mobility','CONN_HO')}"
        if scenario == obj.get("goal"):
            scenario = f"{scenario} @ {cfg.get('RAT','NR_SA')}/{cfg.get('Mobility','CONN_HO')}"
        pass_criteria = r.get("pass_criteria", [])
        if not isinstance(pass_criteria, list):
            pass_criteria = [str(pass_criteria)]
        req_metrics = _extract_req_metrics(req)
        for m in req_metrics:
            if m not in pass_criteria:
                pass_criteria.append(m)
        norm.append(
            {
                "row_id": r.get("row_id") or f"ROW-{idx:03d}",
                "req_id": req_id or ((obj.get("linked_reqs") or [f"REQ-{idx:03d}"])[0]),
                "objective_id": obj_id or f"TO-{idx:03d}",
                "scenario": scenario,
                "key_configuration": cfg,
                "pass_criteria": pass_criteria or ["关键指标满足需求标准"],
            }
        )
    return norm


def _normalize_testcases(data: Dict[str, Any]) -> Dict[str, Any]:
    tcs = data.get("testcases", [])
    norm = []
    for idx, tc in enumerate(tcs, start=1):
        if not isinstance(tc, dict):
            continue
        steps = tc.get("steps", [])
        if isinstance(steps, list):
            norm_steps = []
            for s in steps:
                if not isinstance(s, dict):
                    continue
                norm_steps.append(
                    {
                        "action": s.get("action") or "CHECK",
                        "params": s.get("params") or {"description": s.get("description", "")},
                    }
                )
            steps = norm_steps
        trace = tc.get("trace") or tc.get("traceability") or {}
        if not isinstance(trace, dict):
            trace = {}
        norm.append(
            {
                "tc_id": tc.get("tc_id") or tc.get("testcase_id") or tc.get("id") or f"TC-{idx:03d}",
                "objective_id": tc.get("objective_id") or tc.get("objectiveId") or "TO-001",
                "title": tc.get("title") or f"测试用例-{idx}",
                "tags": tc.get("tags") if isinstance(tc.get("tags"), list) else (tc.get("labels") if isinstance(tc.get("labels"), list) else [str(tc.get("tags") or tc.get("labels") or "Regression")]),
                "preconditions": tc.get("preconditions")
                if isinstance(tc.get("preconditions"), list)
                else (tc.get("precondition") if isinstance(tc.get("precondition"), list) else [str(tc.get("precondition") or "待补充前置条件")]),
                "steps": steps,
                "expected": tc.get("expected")
                if isinstance(tc.get("expected"), list)
                else (tc.get("expected_results") if isinstance(tc.get("expected_results"), list) else [str(tc.get("expected") or tc.get("expected_results") or "待补充期望结果")]),
                "pass_fail": tc.get("pass_fail")
                if isinstance(tc.get("pass_fail"), list)
                else (tc.get("criteria") if isinstance(tc.get("criteria"), list) else [str(tc.get("pass_fail") or tc.get("criteria") or "待补充通过条件")]),
                "observability": tc.get("observability")
                or {"must_capture": ["modem_log", "logcat"], "assertions": ["ASSERT_IMS_REGISTERED"]},
                "failure_taxonomy": tc.get("failure_taxonomy")
                or [{"code": "TC_FAIL", "signals": ["unknown"], "likely_owner": "UNKNOWN"}],
                "trace": {
                    "req_ids": trace.get("req_ids") or trace.get("requirements") or [],
                    "source_refs": trace.get("source_refs") or trace.get("sources") or ["USER_INPUT"],
                },
            }
        )
    data["testcases"] = norm
    return data


def _chunked(items: List[Any], size: int) -> List[List[Any]]:
    if size <= 0:
        size = 20
    return [items[i : i + size] for i in range(0, len(items), size)]


def _fallback_testcases_from_integrated(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for idx, r in enumerate(rows, start=1):
        cfg = r.get("key_configuration", {}) if isinstance(r.get("key_configuration", {}), dict) else {}
        out.append(
            {
                "tc_id": f"TC-{idx:03d}",
                "objective_id": r.get("objective_id", "TO-001"),
                "title": r.get("scenario", f"场景-{idx}"),
                "tags": ["MatrixDriven", "P1"],
                "preconditions": ["环境配置与矩阵组合已生效"],
                "steps": [
                    {"action": "SET_NETWORK_PROFILE", "params": cfg},
                    {"action": "TRIGGER_REGISTRATION", "params": {"mode": cfg.get("RAT", "NR_SA")}},
                    {"action": "WAIT", "params": {"timeout_s": 60}},
                    {"action": "CHECK", "params": {"item": "SERVICE_READY"}},
                    {"action": "COLLECT_LOG", "params": {"items": ["modem_log", "logcat"]}},
                ],
                "expected": [r.get("scenario", "场景通过")],
                "pass_fail": r.get("pass_criteria", []) if isinstance(r.get("pass_criteria", []), list) else [str(r.get("pass_criteria", ""))],
                "observability": {"must_capture": ["modem_log", "logcat"], "assertions": ["ASSERT_ATTACH_SUCCESS"]},
                "failure_taxonomy": [{"code": "MATRIX_FAIL", "signals": ["criteria_not_met"], "likely_owner": "MODEM_OR_NETWORK"}],
                "trace": {"req_ids": [r.get("req_id", "")], "source_refs": [r.get("row_id", f"ROW-{idx:03d}")]},
            }
        )
    return out


def _normalize_scripts(data: Dict[str, Any]) -> Dict[str, Any]:
    scripts = data.get("scripts", [])
    norm = []
    for idx, sc in enumerate(scripts, start=1):
        if not isinstance(sc, dict):
            continue
        mapping = sc.get("actions_mapping")
        if not mapping:
            raw_steps = (sc.get("mapping") or {}).get("steps", [])
            mapping = []
            for st in raw_steps:
                if isinstance(st, dict):
                    mapping.append(
                        {
                            "action": st.get("action", "CHECK"),
                            "impl": st.get("method") or st.get("provider") or "framework_adapter",
                        }
                    )
        harness_val = sc.get("harness")
        if not harness_val:
            harnesses = sc.get("harnesses") or []
            harness_val = {"type": "+".join(harnesses) if harnesses else "ANDROID_UIA+PY_AT", "version": "v2"}
        norm.append(
            {
                "script_id": sc.get("script_id") or f"SC-{idx:03d}",
                "tc_id": sc.get("tc_id") or f"TC-{idx:03d}",
                "harness": harness_val,
                "dependencies": sc.get("dependencies") or ["adb", "uiautomator2", "pyserial"],
                "inputs": sc.get("inputs") or {"device_id": "adb-serial", "at_port": "/dev/ttyUSB0"},
                "actions_mapping": mapping or [],
                "artifacts": sc.get("artifacts")
                or {"collect": ["logcat.txt", "modem.log"], "naming": "by_tc_id_timestamp"},
                "timeouts": sc.get("timeouts") or {"global_s": 900, "step_s": 60},
            }
        )
    data["scripts"] = norm
    data.setdefault("gaps", [])
    data.setdefault("recommended_framework_extensions", [])
    return data


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
                    "open_questions": ["请确认通过/失败阈值"],
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
        for req in exec_res.get("final_requirements", []):
            if isinstance(req, dict):
                req["persona_sources"] = req.get("persona_sources") or ["PRD", "Carrier", "UX"]
        shared["requirement_spec"] = exec_res
        _trace(shared, "SynthesisNode")
        _emit(shared, "module_result", {"module": "requirement_spec", "data": exec_res})
        return "default"


class TestDesignNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "TestDesignNode")
        return {
            "final_requirements": shared["requirement_spec"].get("final_requirements", []),
            "questions_to_ask": shared["requirement_spec"].get("questions_to_ask", []),
            "assumptions": shared["requirement_spec"].get("assumptions", []),
            "persona_reviews": shared.get("persona_reviews", {}),
            "product_profile": shared.get("product_profile", {}),
            "supervisor_feedback": shared.get("design_supervisor_feedback", ""),
        }

    def exec(self, prep_res):
        reqs = prep_res["final_requirements"]
        def _custom(data: Any):
            if not isinstance(data.get("objectives", []), list):
                raise ValueError("objectives must be a list")
            if not data.get("objectives"):
                raise ValueError("objectives must not be empty")

        data = run_json_agent_strict_with_retry(
            shared=self._shared,
            template_name="test_designer.txt",
            variables={
                "final_requirements_json": json.dumps(reqs, ensure_ascii=False),
                "constraints_json": json.dumps(
                    {
                        "lab_resources": "TBD",
                        "time_budget": "TBD",
                        "questions_to_ask": prep_res.get("questions_to_ask", []),
                        "assumptions": prep_res.get("assumptions", []),
                        "persona_reviews": prep_res.get("persona_reviews", {}),
                        "product_profile": prep_res.get("product_profile", {}),
                        "supervisor_feedback": prep_res.get("supervisor_feedback", ""),
                    },
                    ensure_ascii=False,
                ),
                "return_schema": json.dumps(TEST_DESIGN_SCHEMA, ensure_ascii=False),
                "output_schema": json.dumps(TEST_DESIGN_SCHEMA, ensure_ascii=False),
            },
            schema=TEST_DESIGN_SCHEMA,
            warn_tag="TestDesignNode",
            custom_validator=_custom,
        )
        normalized = _normalize_objectives(data, reqs)

        def _matrix_custom(data: Any):
            rows = data.get("integrated_matrix", [])
            if not isinstance(rows, list) or not rows:
                raise ValueError("integrated_matrix must be non-empty list")

        matrix_data = run_json_agent_strict_with_retry(
            shared=self._shared,
            template_name="integrated_matrix_designer.txt",
            variables={
                "final_requirements_json": json.dumps(reqs, ensure_ascii=False),
                "objectives_json": json.dumps(normalized.get("objectives", []), ensure_ascii=False),
                "coverage_matrices_json": json.dumps(normalized.get("coverage_matrices", []), ensure_ascii=False),
                "output_schema": json.dumps(INTEGRATED_MATRIX_SCHEMA, ensure_ascii=False),
            },
            schema=INTEGRATED_MATRIX_SCHEMA,
            warn_tag="IntegratedMatrixNode",
            custom_validator=_matrix_custom,
        )
        integrated_rows = _normalize_integrated_rows(matrix_data.get("integrated_matrix", []), reqs, normalized.get("objectives", []))
        if not integrated_rows:
            raise RuntimeError("IntegratedMatrixNode: normalized integrated_matrix is empty")
        normalized["integrated_matrix"] = integrated_rows
        normalized["generation_meta"] = {
            "design_generated_by_llm": True,
            "integrated_matrix_generated_by_llm": True,
            "design_prompt": "test_designer.txt",
            "integrated_prompt": "integrated_matrix_designer.txt",
        }
        return normalized

    def _run(self, shared):
        self._shared = shared
        return super()._run(shared)

    def post(self, shared, prep_res, exec_res):
        validate_jsonschema(exec_res, TEST_DESIGN_SCHEMA)
        objectives = exec_res.get("objectives", [])
        validate_list_of_dict(objectives, TEST_OBJECTIVE_REQUIRED_KEYS, "objectives")
        shared["test_design_spec"] = exec_res
        _trace(shared, "TestDesignNode")
        _emit(shared, "module_result", {"module": "test_design_spec", "data": exec_res})
        return "default"


class TestDesignSupervisorNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "TestDesignSupervisorNode")
        return {
            "requirement_spec": shared.get("requirement_spec", {}),
            "test_design_spec": shared.get("test_design_spec", {}),
            "retry_count": int(shared.get("design_retry_count", 0)),
            "max_retries": int(shared.get("design_max_retries", 2)),
        }

    def exec(self, prep_res):
        req_spec = prep_res.get("requirement_spec", {})
        design = prep_res.get("test_design_spec", {})
        issues: List[str] = []
        reqs = req_spec.get("final_requirements", [])
        objectives = design.get("objectives", [])
        integrated = design.get("integrated_matrix", [])

        if not isinstance(objectives, list) or not objectives:
            issues.append("objectives为空")
        if not isinstance(integrated, list) or not integrated:
            issues.append("integrated_matrix为空")

        req_ids = {r.get("req_id") for r in reqs if isinstance(r, dict) and r.get("req_id")}
        covered_req_ids = {row.get("req_id") for row in (integrated or []) if isinstance(row, dict) and row.get("req_id")}
        missing = sorted([rid for rid in req_ids if rid not in covered_req_ids])
        if missing:
            issues.append(f"整合覆盖矩阵缺少需求覆盖: {', '.join(missing)}")

        numeric_req = []
        for r in reqs:
            for txt in (r.get("acceptance", {}).get("pass_fail", []) if isinstance(r, dict) else []):
                t = str(txt)
                if any(ch.isdigit() for ch in t):
                    numeric_req.append(t)
        if numeric_req and integrated:
            pass_text = " ".join(
                [
                    " ".join(row.get("pass_criteria", []) if isinstance(row.get("pass_criteria", []), list) else [str(row.get("pass_criteria", ""))])
                    for row in integrated
                    if isinstance(row, dict)
                ]
            )
            if sum(1 for m in numeric_req if m in pass_text) < max(1, len(numeric_req) // 3):
                issues.append("需求中的数值型验收标准在设计稿中保留不足")

        approved = len(issues) == 0
        return {"approved": approved, "issues": issues}

    def post(self, shared, prep_res, exec_res):
        if exec_res["approved"]:
            shared["design_supervisor_feedback"] = ""
            _emit(shared, "module_result", {"module": "test_design_supervisor", "data": exec_res})
            return "default"

        retry_count = prep_res["retry_count"] + 1
        shared["design_retry_count"] = retry_count
        shared["design_supervisor_feedback"] = "；".join(exec_res["issues"])
        shared.setdefault("warnings", []).append(
            f"TestDesignSupervisorNode: 质量审查未通过，第{retry_count}次回流: {' | '.join(exec_res['issues'])}"
        )
        _emit(shared, "module_result", {"module": "test_design_supervisor", "data": exec_res})
        if retry_count <= prep_res["max_retries"]:
            return "retry"
        shared.setdefault("warnings", []).append("TestDesignSupervisorNode: 达到最大回流次数，继续后续流程")
        return "default"


class TestCaseGeneratorNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "TestCaseGeneratorNode")
        return {
            "objectives": shared["test_design_spec"].get("objectives", []),
            "coverage": shared["test_design_spec"].get("coverage_matrices", []),
            "integrated_matrix": shared["test_design_spec"].get("integrated_matrix", []),
            "action_vocabulary": shared["action_vocabulary"],
            "questions_to_ask": shared["requirement_spec"].get("questions_to_ask", []),
            "assumptions": shared["requirement_spec"].get("assumptions", []),
            "persona_reviews": shared.get("persona_reviews", {}),
        }

    def exec(self, prep_res):
        objectives = prep_res["objectives"]
        integrated = prep_res.get("integrated_matrix", [])
        if not isinstance(integrated, list) or not integrated:
            fallback = {"testcases": _fallback_testcases_from_objectives(objectives)}
            data = run_json_agent_with_retry(
                shared=self._shared,
                template_name="test_case_generator.txt",
                variables={
                    "integrated_matrix_json": json.dumps([], ensure_ascii=False),
                    "objectives_json": json.dumps(prep_res["objectives"], ensure_ascii=False),
                    "coverage_json": json.dumps(
                        {
                            "coverage_matrices": prep_res["coverage"],
                            "questions_to_ask": prep_res.get("questions_to_ask", []),
                            "assumptions": prep_res.get("assumptions", []),
                            "persona_reviews": prep_res.get("persona_reviews", {}),
                        },
                        ensure_ascii=False,
                    ),
                    "action_vocabulary_json": json.dumps(prep_res["action_vocabulary"], ensure_ascii=False),
                    "return_schema": json.dumps(TESTCASE_SCHEMA, ensure_ascii=False),
                    "output_schema": json.dumps(TESTCASE_SCHEMA, ensure_ascii=False),
                },
                schema=TESTCASE_SCHEMA,
                fallback=fallback,
                warn_tag="TestCaseGeneratorNode",
            )
            return _normalize_testcases(data)

        all_tcs: List[Dict[str, Any]] = []
        chunks = _chunked(integrated, 16)
        for i, chunk in enumerate(chunks, start=1):
            fallback = {"testcases": _fallback_testcases_from_integrated(chunk)}
            try:
                data = run_json_agent_strict_with_retry(
                    shared=self._shared,
                    template_name="test_case_generator.txt",
                    variables={
                        "integrated_matrix_json": json.dumps(chunk, ensure_ascii=False),
                        "objectives_json": json.dumps(prep_res["objectives"], ensure_ascii=False),
                        "coverage_json": json.dumps(
                            {
                                "coverage_matrices": prep_res["coverage"],
                                "questions_to_ask": prep_res.get("questions_to_ask", []),
                                "assumptions": prep_res.get("assumptions", []),
                                "persona_reviews": prep_res.get("persona_reviews", {}),
                                "batch_index": i,
                                "batch_total": len(chunks),
                            },
                            ensure_ascii=False,
                        ),
                        "action_vocabulary_json": json.dumps(prep_res["action_vocabulary"], ensure_ascii=False),
                        "return_schema": json.dumps(TESTCASE_SCHEMA, ensure_ascii=False),
                        "output_schema": json.dumps(TESTCASE_SCHEMA, ensure_ascii=False),
                    },
                    schema=TESTCASE_SCHEMA,
                    warn_tag=f"TestCaseGeneratorNode-Batch{i}",
                    custom_validator=lambda d: isinstance(d.get("testcases", []), list) or (_ for _ in ()).throw(ValueError("testcases must be list")),
                )
            except Exception as exc:
                self._shared.setdefault("warnings", []).append(f"TestCaseGeneratorNode-Batch{i}: 严格生成失败，回退该批: {exc}")
                data = fallback
            norm = _normalize_testcases(data)
            all_tcs.extend(norm.get("testcases", []))

        return {"testcases": all_tcs}

    def _run(self, shared):
        self._shared = shared
        return super()._run(shared)

    def post(self, shared, prep_res, exec_res):
        testcases = exec_res.get("testcases", [])
        validate_list_of_dict(testcases, TESTCASE_REQUIRED_KEYS, "testcases")
        ensure_actions_in_vocabulary(testcases, prep_res["action_vocabulary"])
        shared["test_case_spec"] = exec_res
        _trace(shared, "TestCaseGeneratorNode")
        _emit(shared, "module_result", {"module": "test_case_spec", "data": exec_res})
        return "default"


class TestCaseBatchGenNode(AsyncNode):
    async def prep_async(self, shared):
        _set_current_node(shared, "TestCaseBatchGenNode")
        return {
            "batch_index": int(self.params.get("batch_index", 0)),
            "batch_total": int(self.params.get("batch_total", 1)),
            "integrated_chunk": self.params.get("integrated_chunk", []),
            "objectives": shared["test_design_spec"].get("objectives", []),
            "coverage": shared["test_design_spec"].get("coverage_matrices", []),
            "action_vocabulary": shared["action_vocabulary"],
            "questions_to_ask": shared["requirement_spec"].get("questions_to_ask", []),
            "assumptions": shared["requirement_spec"].get("assumptions", []),
            "persona_reviews": shared.get("persona_reviews", {}),
            "supervisor_feedback": shared.get("testcase_supervisor_feedback", ""),
        }

    async def exec_async(self, prep_res):
        chunk = prep_res["integrated_chunk"]
        if not chunk:
            return {"testcases": _fallback_testcases_from_objectives(prep_res.get("objectives", []))}
        fallback = {"testcases": _fallback_testcases_from_integrated(chunk)}
        try:
            data = await asyncio.to_thread(
                run_json_agent_strict_with_retry,
                shared=self._shared,
                template_name="test_case_generator.txt",
                variables={
                    "integrated_matrix_json": json.dumps(chunk, ensure_ascii=False),
                    "objectives_json": json.dumps(prep_res["objectives"], ensure_ascii=False),
                    "coverage_json": json.dumps(
                        {
                            "coverage_matrices": prep_res["coverage"],
                            "questions_to_ask": prep_res.get("questions_to_ask", []),
                            "assumptions": prep_res.get("assumptions", []),
                            "persona_reviews": prep_res.get("persona_reviews", {}),
                            "batch_index": prep_res["batch_index"] + 1,
                            "batch_total": prep_res["batch_total"],
                            "supervisor_feedback": prep_res.get("supervisor_feedback", ""),
                        },
                        ensure_ascii=False,
                    ),
                    "action_vocabulary_json": json.dumps(prep_res["action_vocabulary"], ensure_ascii=False),
                    "return_schema": json.dumps(TESTCASE_SCHEMA, ensure_ascii=False),
                    "output_schema": json.dumps(TESTCASE_SCHEMA, ensure_ascii=False),
                },
                schema=TESTCASE_SCHEMA,
                warn_tag=f"TestCaseBatchGenNode-Batch{prep_res['batch_index'] + 1}",
                custom_validator=lambda d: isinstance(d.get("testcases", []), list)
                or (_ for _ in ()).throw(ValueError("testcases must be list")),
            )
        except Exception as exc:
            self._shared.setdefault("warnings", []).append(
                f"TestCaseBatchGenNode-Batch{prep_res['batch_index'] + 1}: 严格生成失败，回退该批: {exc}"
            )
            data = fallback
        return _normalize_testcases(data)

    async def post_async(self, shared, prep_res, exec_res):
        batches = shared.setdefault("_testcase_batches", {})
        batches[prep_res["batch_index"]] = exec_res.get("testcases", [])
        _emit(
            shared,
            "module_result",
            {
                "module": "test_case_batch",
                "data": {
                    "batch_index": prep_res["batch_index"] + 1,
                    "batch_total": prep_res["batch_total"],
                    "count": len(exec_res.get("testcases", [])),
                },
            },
        )
        return "default"

    async def _run_async(self, shared):
        self._shared = shared
        return await super()._run_async(shared)


class FinalizeTestCaseNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "FinalizeTestCaseNode")
        return {
            "batches": shared.get("_testcase_batches", {}),
            "action_vocabulary": shared.get("action_vocabulary", DEFAULT_ACTION_VOCABULARY),
        }

    def exec(self, prep_res):
        batches = prep_res["batches"] if isinstance(prep_res["batches"], dict) else {}
        all_tcs: List[Dict[str, Any]] = []
        for idx in sorted(batches.keys()):
            all_tcs.extend(batches[idx])
        return {"testcases": all_tcs}

    def post(self, shared, prep_res, exec_res):
        testcases = exec_res.get("testcases", [])
        validate_list_of_dict(testcases, TESTCASE_REQUIRED_KEYS, "testcases")
        ensure_actions_in_vocabulary(testcases, prep_res["action_vocabulary"])
        shared["test_case_spec"] = exec_res
        _trace(shared, "FinalizeTestCaseNode")
        _emit(shared, "module_result", {"module": "test_case_spec", "data": exec_res})
        return "default"


class TestCaseSupervisorNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "TestCaseSupervisorNode")
        return {
            "requirement_spec": shared.get("requirement_spec", {}),
            "test_case_spec": shared.get("test_case_spec", {}),
            "retry_count": int(shared.get("testcase_retry_count", 0)),
            "max_retries": int(shared.get("testcase_max_retries", 2)),
        }

    def exec(self, prep_res):
        reqs = prep_res.get("requirement_spec", {}).get("final_requirements", [])
        tcs = prep_res.get("test_case_spec", {}).get("testcases", [])
        issues: List[str] = []
        if not isinstance(tcs, list) or not tcs:
            issues.append("testcases为空")
            return {"approved": False, "issues": issues}

        req_ids = {r.get("req_id") for r in reqs if isinstance(r, dict) and r.get("req_id")}
        covered = set()
        for tc in tcs:
            if isinstance(tc, dict):
                trace = tc.get("trace", {})
                if isinstance(trace, dict):
                    covered.update([x for x in trace.get("req_ids", []) if x])
        miss = sorted([rid for rid in req_ids if rid not in covered])
        if miss:
            issues.append(f"用例trace缺少需求覆盖: {', '.join(miss)}")

        numeric_req = []
        for r in reqs:
            for txt in (r.get("acceptance", {}).get("pass_fail", []) if isinstance(r, dict) else []):
                t = str(txt)
                if any(ch.isdigit() for ch in t):
                    numeric_req.append(t)
        pass_text = " ".join(
            [
                " ".join(tc.get("pass_fail", []) if isinstance(tc.get("pass_fail", []), list) else [str(tc.get("pass_fail", ""))])
                for tc in tcs
                if isinstance(tc, dict)
            ]
        )
        if numeric_req and sum(1 for m in numeric_req if m in pass_text) < max(1, len(numeric_req) // 3):
            issues.append("需求中的数值型验收标准在用例pass_fail中保留不足")

        approved = len(issues) == 0
        return {"approved": approved, "issues": issues}

    def post(self, shared, prep_res, exec_res):
        if exec_res["approved"]:
            shared["testcase_supervisor_feedback"] = ""
            _emit(shared, "module_result", {"module": "test_case_supervisor", "data": exec_res})
            return "default"

        retry_count = prep_res["retry_count"] + 1
        shared["testcase_retry_count"] = retry_count
        shared["testcase_supervisor_feedback"] = "；".join(exec_res["issues"])
        shared.setdefault("warnings", []).append(
            f"TestCaseSupervisorNode: 质量审查未通过，第{retry_count}次回流: {' | '.join(exec_res['issues'])}"
        )
        _emit(shared, "module_result", {"module": "test_case_supervisor", "data": exec_res})
        if retry_count <= prep_res["max_retries"]:
            return "retry"
        shared.setdefault("warnings", []).append("TestCaseSupervisorNode: 达到最大回流次数，继续后续流程")
        return "default"


class HarnessMapperNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "HarnessMapperNode")
        return {"testcases": shared["test_case_spec"].get("testcases", []), "capabilities": shared["capabilities"]}

    def exec(self, prep_res):
        fallback_scripts = []
        for tc in prep_res["testcases"]:
            fallback_scripts.append(
                {
                    "script_id": f"SC-{tc['tc_id']}",
                    "tc_id": tc["tc_id"],
                    "harness": {"type": "ANDROID_UIA+PY_AT", "version": "v2"},
                    "dependencies": ["adb", "uiautomator2", "pyserial"],
                    "inputs": {"device_id": "adb-serial", "at_port": "/dev/ttyUSB0"},
                    "actions_mapping": [
                        {"action": s["action"], "impl": "framework_adapter"} for s in tc.get("steps", [])
                    ],
                    "artifacts": {"collect": ["logcat.txt", "modem.log"], "naming": "by_tc_id_timestamp"},
                    "timeouts": {"global_s": 900, "step_s": 60},
                }
            )
        fallback = {"scripts": fallback_scripts, "gaps": [], "recommended_framework_extensions": []}

        def _custom(data: Any):
            if not isinstance(data.get("scripts", []), list):
                raise ValueError("scripts must be a list")

        data = run_json_agent_with_retry(
            shared=self._shared,
            template_name="harness_mapper.txt",
            variables={
                "testcases_json": json.dumps(prep_res["testcases"], ensure_ascii=False),
                "capabilities_json": json.dumps(prep_res["capabilities"], ensure_ascii=False),
                "return_schema": json.dumps(SCRIPT_PLAN_SCHEMA, ensure_ascii=False),
                "output_schema": json.dumps(SCRIPT_PLAN_SCHEMA, ensure_ascii=False),
            },
            schema=SCRIPT_PLAN_SCHEMA,
            fallback=fallback,
            warn_tag="HarnessMapperNode",
            custom_validator=_custom,
        )
        return _normalize_scripts(data)

    def _run(self, shared):
        self._shared = shared
        return super()._run(shared)

    def post(self, shared, prep_res, exec_res):
        scripts = exec_res.get("scripts", [])
        validate_list_of_dict(scripts, SCRIPTSPEC_REQUIRED_KEYS, "scripts")
        shared["script_spec"] = exec_res
        _trace(shared, "HarnessMapperNode")
        _emit(shared, "module_result", {"module": "script_spec", "data": exec_res})
        return "default"


class ScriptWriterNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "ScriptWriterNode")
        return {"script_spec": shared["script_spec"], "assertion_vocabulary": shared["assertion_vocabulary"]}

    def exec(self, prep_res):
        fallback = """
# 测试代码（参考）
```python
import json
import time


def run_case(inputs):
    result = {"pass": True, "artifacts": []}
    try:
        time.sleep(1)
        result["artifacts"].extend(["logcat.txt", "modem.log"])
    except Exception as exc:
        result["pass"] = False
        result["error"] = str(exc)

    with open("run_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_case({})
```
""".strip()

        return run_text_agent(
            shared=self._shared,
            template_name="script_writer.txt",
            variables={
                "script_spec_json": json.dumps(prep_res["script_spec"], ensure_ascii=False),
                "code_template": "Python pytest runner with adapters",
            },
            fallback=fallback,
            warn_tag="ScriptWriterNode",
        )

    def _run(self, shared):
        self._shared = shared
        return super()._run(shared)

    def post(self, shared, prep_res, exec_res):
        shared["test_code_reference"] = exec_res
        _trace(shared, "ScriptWriterNode")
        _emit(shared, "module_result", {"module": "test_code_reference", "data": exec_res})
        return "default"


class AssembleResultNode(Node):
    def prep(self, shared):
        _set_current_node(shared, "AssembleResultNode")
        return shared

    def exec(self, prep_res):
        req_spec = prep_res.get("requirement_spec", {})
        design = prep_res.get("test_design_spec", {})
        case_spec = prep_res.get("test_case_spec", {})
        script_spec = prep_res.get("script_spec", {})
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
                "Test Design",
                "Test Case Generation",
                "Script Planning",
                "Script Generation",
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
                "script_spec": script_spec,
            },
            "artifacts": {
                "test_requirements": "\n".join(req_lines),
                "review_process": json.dumps(persona_reviews, ensure_ascii=False, indent=2),
                "test_design": json.dumps(design, ensure_ascii=False, indent=2),
                "test_cases": json.dumps(case_spec, ensure_ascii=False, indent=2),
                "test_code_reference": prep_res.get("test_code_reference", ""),
            },
            "trace": prep_res.get("trace", []),
        }

    def post(self, shared, prep_res, exec_res):
        shared["final_result"] = exec_res
        _trace(shared, "AssembleResultNode")
        _emit(shared, "final_result", exec_res)
        return None
