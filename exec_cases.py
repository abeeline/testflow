"""把测试用例落地为各执行平台可直接使用的 JSON case。

每条测试用例按验收方案分流到四条路线：
- artemis:   手机实网系统测试，导出 Artemis 用例库格式（artemis-case-library v1, profile=flash）
- at_agent:  模组 AT 实网测试，导出 AT Agent 用例库格式（artemis-case-library v1, profile=at）
- amarisoft: Amarisoft 模拟基站，导出给 Amarisoft Agent 的 case（关键 PHY/协议参数 + 步骤 + 期望信令）
- protocol:  协议分析仪 / 仿真仪表，导出协议流程测试需求（信令流程、IE、检查点），供 PRTest 后续落地
"""
import asyncio
import datetime as dt
import json
import uuid
from typing import Any, Dict, List

from pocketflow import AsyncNode
from utils.agent_runner import run_json_agent_with_retry

ROUTES = ["artemis", "at_agent", "amarisoft", "protocol"]

ROUTE_LABELS = {
    "artemis": "Artemis 手机实网用例",
    "at_agent": "AT Agent 模组实网用例",
    "amarisoft": "Amarisoft 模拟基站用例",
    "protocol": "协议流程测试需求（PRTest）",
}

ROUTE_PROMPTS = {
    "artemis": "exec_case_artemis.txt",
    "at_agent": "exec_case_at_agent.txt",
    "amarisoft": "exec_case_amarisoft.txt",
    "protocol": "exec_case_protocol.txt",
}

ROUTE_LIST_KEY = {"artemis": "cases", "at_agent": "cases", "amarisoft": "cases", "protocol": "items"}

MODULE_FORM_FACTORS = {"通信模组", "车载模组"}
PHONE_FORM_FACTORS = {"智能手机", "功能手机", "穿戴产品"}

# 与 Artemis / AT Agent 的 PortableCaseTask 字段上限保持一致（导入接口 extra=forbid）。
_TITLE_MAX = 120
_GOAL_MAX = 20000
_TEXT_MAX = 4000
_GROUP_MAX = 80
_CODE_MAX = 120
_REQ_MAX = 2000

# 稳定的命名空间，同一个 tc_id 每次导出得到同一个 id，重复导入时平台能识别。
_CASE_NS = uuid.UUID("6f1c2a52-9d0e-4b7e-8f43-7a1d2c5e9b10")


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "；".join(_text(v) for v in value if _text(v))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _cut(value: Any, limit: int) -> str:
    s = _text(value)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _form_factors(product_profile: Dict[str, Any]) -> set:
    selected = (product_profile or {}).get("selected") or {}
    values = selected.get("form_factor") if isinstance(selected, dict) else None
    return set(values or [])


def route_for_testcase(tc: Dict[str, Any], product_profile: Dict[str, Any]) -> str:
    env = str(((tc.get("test_environment") or {}).get("primary")) or "").upper()
    if env == "AMARISOFT":
        return "amarisoft"
    if env == "PROTOCOL_ANALYZER":
        return "protocol"
    blob = json.dumps(tc, ensure_ascii=False).upper()
    if "AT+" in blob or "AT指令" in blob:
        return "at_agent"
    forms = _form_factors(product_profile)
    if forms & MODULE_FORM_FACTORS and not forms & PHONE_FORM_FACTORS:
        return "at_agent"
    return "artemis"


def _tc_summary(tc: Dict[str, Any]) -> Dict[str, Any]:
    """只给 LLM 必要字段，控制提示词长度。"""
    keys = ["tc_id", "objective_id", "title", "tags", "preconditions", "steps", "expected", "pass_fail",
            "test_environment", "observability", "trace"]
    return {k: tc.get(k) for k in keys if k in tc}


def _requirement_index(requirement_spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for r in (requirement_spec or {}).get("final_requirements", []) or []:
        if isinstance(r, dict) and r.get("req_id"):
            out[str(r["req_id"])] = r
    return out


def _trace_for(tc: Dict[str, Any], req_index: Dict[str, Dict[str, Any]], bug_ids: List[str]) -> Dict[str, Any]:
    trace = tc.get("trace") or {}
    req_ids = [str(x) for x in (trace.get("req_ids") or []) if str(x).strip()]
    return {
        "tc_id": tc.get("tc_id", ""),
        "objective_id": tc.get("objective_id", ""),
        "req_ids": req_ids,
        "row_ids": [str(x) for x in (trace.get("source_refs") or []) if str(x).strip()],
        "req_titles": [str((req_index.get(r) or {}).get("title", "")) for r in req_ids],
        "bug_ids": list(bug_ids),
    }


def _priority(tc: Dict[str, Any], llm_value: Any = None) -> str:
    for v in [llm_value, *(tc.get("tags") or [])]:
        s = str(v or "").upper()
        if s in ("P0", "P1", "P2"):
            return s
    return "P1"


# ---------- 降级结果（LLM 不可用时也能导出可用 case） ----------

def _steps_text(tc: Dict[str, Any]) -> str:
    parts = []
    for i, s in enumerate(tc.get("steps") or [], start=1):
        if not isinstance(s, dict):
            continue
        params = s.get("params") or {}
        p = "，".join(f"{k}={v}" for k, v in params.items()) if isinstance(params, dict) else _text(params)
        parts.append(f"{i}. {s.get('action', '')}" + (f"（{p}）" if p else ""))
    return "\n".join(parts)


def _fallback_route_items(route: str, tcs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for tc in tcs:
        title = _text(tc.get("title")) or tc.get("tc_id", "")
        expected = _text(tc.get("pass_fail")) or _text(tc.get("expected"))
        base = {"source_tc_id": tc.get("tc_id", ""), "title": title}
        if route in ("artemis", "at_agent"):
            goal = title + ("\n" + _steps_text(tc) if tc.get("steps") else "")
            items.append({**base, "goal": goal, "expected_result": expected,
                          "preconditions": _text(tc.get("preconditions")), "group": "", "priority": _priority(tc), "redline": False})
        elif route == "amarisoft":
            items.append({**base, "objective": title, "rat": "", "ue_preconditions": tc.get("preconditions") or [],
                          "cell_config": {}, "core_config": {}, "key_parameters": [],
                          "procedure": [{"step": i + 1, "action": s.get("action", ""), "params": s.get("params") or {}, "expected": ""}
                                        for i, s in enumerate(tc.get("steps") or []) if isinstance(s, dict)],
                          "expected_signaling": [], "pass_criteria": tc.get("pass_fail") or [],
                          "logs_to_capture": (tc.get("observability") or {}).get("must_capture") or []})
        else:
            items.append({**base, "scenario": title, "layers": [], "rat": "", "cell_config": {}, "signaling_flow": [],
                          "parameter_variations": [], "checkpoints": [{"item": x, "expected": ""} for x in (tc.get("expected") or [])],
                          "pass_criteria": tc.get("pass_fail") or [], "references": [], "open_points": ["LLM 未生成，需人工补充信令流程与关键 IE。"]})
    return items


# ---------- 各平台导出格式 ----------

def _artemis_case(item: Dict[str, Any], tc: Dict[str, Any], trace: Dict[str, Any], profile: str) -> Dict[str, Any]:
    tc_id = str(tc.get("tc_id") or item.get("source_tc_id") or "")
    goal = _cut(item.get("goal"), _GOAL_MAX) or _cut(tc.get("title"), _GOAL_MAX) or tc_id
    preconditions = _text(item.get("preconditions"))
    if preconditions:
        goal = _cut(f"前置条件：{preconditions}\n{goal}", _GOAL_MAX)
    req_text = "；".join(f"{r} {t}".strip() for r, t in zip(trace["req_ids"], trace["req_titles"]))
    task = {
        "goal": goal,
        "profile": profile,
        "case_code": _cut(tc_id, _CODE_MAX),
        "group": _cut(item.get("group"), _GROUP_MAX),
        "redline": bool(item.get("redline")),
        "expected_result": _cut(item.get("expected_result"), _TEXT_MAX),
        "test_kind": "verification",
        "bug_ids": trace["bug_ids"][:30],
        "requirements": _cut(req_text, _REQ_MAX),
        "priority": _priority(tc, item.get("priority")),
    }
    return {
        "id": str(uuid.uuid5(_CASE_NS, f"{profile}:{tc_id}:{item.get('title', '')}")),
        "title": _cut(item.get("title") or tc.get("title") or tc_id, _TITLE_MAX),
        "task": task,
    }


def build_bundle(route: str, items: List[Dict[str, Any]], tc_index: Dict[str, Dict[str, Any]],
                 req_index: Dict[str, Dict[str, Any]], bug_ids: List[str]) -> Dict[str, Any]:
    exported_at = _now()
    if route in ("artemis", "at_agent"):
        profile = "flash" if route == "artemis" else "at"
        cases = []
        for item in items:
            tc = tc_index.get(str(item.get("source_tc_id") or ""), {})
            cases.append(_artemis_case(item, tc, _trace_for(tc, req_index, bug_ids), profile))
        # 同一用例拆出多条时 id 可能撞车，按顺序去重。
        seen = set()
        for c in cases:
            while c["id"] in seen:
                c["id"] = str(uuid.uuid4())
            seen.add(c["id"])
        return {"format": "artemis-case-library", "version": 1, "exported_at": exported_at, "cases": cases}

    out_items = []
    for idx, item in enumerate(items, start=1):
        tc = tc_index.get(str(item.get("source_tc_id") or ""), {})
        prefix = "AMS" if route == "amarisoft" else "PRT"
        entry = {"case_id": f"{prefix}-{idx:03d}", **item, "priority": _priority(tc, item.get("priority")),
                 "trace": _trace_for(tc, req_index, bug_ids)}
        out_items.append(entry)
    if route == "amarisoft":
        return {"format": "testflow-amarisoft-case", "version": 1, "exported_at": exported_at, "cases": out_items}
    return {"format": "testflow-protocol-test-requirement", "version": 1, "exported_at": exported_at, "items": out_items}


def build_traceability(tcs: List[Dict[str, Any]], routes: Dict[str, str], bundles: Dict[str, Dict[str, Any]],
                       req_index: Dict[str, Dict[str, Any]], bug_ids: List[str]) -> List[Dict[str, Any]]:
    """需求 → 用例 → 可执行 case 的追溯矩阵。"""
    exec_ids: Dict[str, List[str]] = {}
    for route, bundle in bundles.items():
        for c in bundle.get("cases") or bundle.get("items") or []:
            tc_id = (c.get("task") or {}).get("case_code") if route in ("artemis", "at_agent") else (c.get("trace") or {}).get("tc_id")
            exec_ids.setdefault(str(tc_id or ""), []).append(c.get("case_id") or c.get("id"))
    rows = []
    for tc in tcs:
        tc_id = str(tc.get("tc_id") or "")
        t = _trace_for(tc, req_index, bug_ids)
        route = routes.get(tc_id, "")
        rows.append({
            "bug_ids": t["bug_ids"],
            "req_ids": t["req_ids"],
            "req_titles": t["req_titles"],
            "objective_id": t["objective_id"],
            "row_ids": t["row_ids"],
            "tc_id": tc_id,
            "tc_title": tc.get("title", ""),
            "test_environment": (tc.get("test_environment") or {}).get("primary", ""),
            "route": route,
            "route_label": ROUTE_LABELS.get(route, route),
            "exec_case_ids": exec_ids.get(tc_id, []),
        })
    return rows


class ExecutableCaseNode(AsyncNode):
    """按路线并行调用 LLM，把测试用例转换成各平台 case。"""

    async def prep_async(self, shared):
        shared["current_node"] = "ExecutableCaseNode"
        q = shared.get("event_queue")
        if q:
            q.put_nowait({"type": "node_running", "payload": {"node": "ExecutableCaseNode"}})
        tcs = [tc for tc in (shared.get("test_case_spec") or {}).get("testcases", []) if isinstance(tc, dict)]
        profile = shared.get("product_profile") or {}
        overrides = shared.get("route_overrides") or {}
        routes = {}
        for tc in tcs:
            tc_id = str(tc.get("tc_id") or "")
            forced = str(overrides.get(tc_id) or "")
            routes[tc_id] = forced if forced in ROUTES else route_for_testcase(tc, profile)
        return {"testcases": tcs, "routes": routes, "product_profile": profile}

    async def exec_async(self, prep_res):
        tcs = prep_res["testcases"]
        routes = prep_res["routes"]
        shared = self._shared
        req_index = _requirement_index(shared.get("requirement_spec") or {})
        requirements = [{"req_id": k, "title": v.get("title", ""), "description": v.get("description", "")} for k, v in req_index.items()]

        groups: Dict[str, List[Dict[str, Any]]] = {r: [] for r in ROUTES}
        for tc in tcs:
            groups[routes[str(tc.get("tc_id") or "")]].append(tc)

        async def run_route(route: str, route_tcs: List[Dict[str, Any]]):
            list_key = ROUTE_LIST_KEY[route]
            schema = {"type": "object", "required": [list_key],
                      "properties": {list_key: {"type": "array", "items": {"type": "object"}}}}
            fallback = {list_key: _fallback_route_items(route, route_tcs)}
            data = await asyncio.to_thread(
                run_json_agent_with_retry,
                shared=shared,
                template_name=ROUTE_PROMPTS[route],
                variables={
                    "testcases_json": json.dumps([_tc_summary(tc) for tc in route_tcs], ensure_ascii=False),
                    "requirements_json": json.dumps(requirements, ensure_ascii=False),
                    "product_profile_json": json.dumps(prep_res["product_profile"].get("selected", {}), ensure_ascii=False),
                    "last_error": "",
                },
                schema=schema,
                fallback=fallback,
                warn_tag=f"ExecutableCaseNode-{route}",
            )
            items = [x for x in data.get(list_key, []) if isinstance(x, dict)]
            # LLM 漏掉的用例用降级结果补上，保证每条用例都能落地。
            covered = {str(x.get("source_tc_id") or "") for x in items}
            missing = [tc for tc in route_tcs if str(tc.get("tc_id") or "") not in covered]
            if missing and data is not fallback:
                shared.setdefault("warnings", []).append(
                    f"ExecutableCaseNode-{route}: {len(missing)} 条用例未被 LLM 覆盖，已用降级结果补齐")
                items.extend(_fallback_route_items(route, missing))
            return route, items

        jobs = [run_route(r, g) for r, g in groups.items() if g]
        results = dict(await asyncio.gather(*jobs)) if jobs else {}

        tc_index = {str(tc.get("tc_id") or ""): tc for tc in tcs}
        bug_ids = [str(b) for b in (shared.get("bug_ids") or []) if str(b).strip()]
        bundles = {r: build_bundle(r, items, tc_index, req_index, bug_ids) for r, items in results.items()}
        return {
            "generated_at": _now(),
            "summary": {r: len(groups[r]) for r in ROUTES},
            "route_labels": ROUTE_LABELS,
            "routes": routes,
            "bundles": bundles,
            "traceability": build_traceability(tcs, routes, bundles, req_index, bug_ids),
        }

    async def post_async(self, shared, prep_res, exec_res):
        shared["executable_cases"] = exec_res
        shared.setdefault("trace", []).append({"node": "ExecutableCaseNode", "time": _now()})
        q = shared.get("event_queue")
        if q:
            q.put_nowait({"type": "module_result", "payload": {"module": "executable_cases", "data": exec_res["summary"]}})
        return "default"

    async def _run_async(self, shared):
        self._shared = shared
        return await super()._run_async(shared)
