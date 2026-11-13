"""测试架构图：把一次测试设计汇成一棵树，输出成一份可以离线打开的 HTML。

    一级模块 → 需求 → 测试点（按测试技术着色）→ 用例

同一份数据给三个视图用：脑图（看整体结构）、覆盖矩阵（需求 × 测试技术，看哪里是空的）、
评审关注点（没有测试点的需求、高优先级只测了正常流程、测试点还没出用例……）。
测试设计完成后就能生成；用例和可执行用例出来以后，同一张图上会带出用例编号。
"""
import json
import time
from typing import Any, Dict, List

from core.grouping import UNGROUPED, requirement_group
from core.tcd import TECHNIQUE_LABELS, TECHNIQUES, normalize_technique
from utils.paths import STATIC_DIR

TEMPLATE_NAME = "design_map_template.html"
HIGH_PRIORITIES = ("P0", "P1")
_ENV_SHORT = {"AMARISOFT": "Amarisoft", "PROTOCOL_ANALYZER": "协议仪表", "ARTEMIS": "Artemis", "AT_AGENT": "AT", "FIELD": "外场"}


def _text(value: Any, limit: int = 0) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit] if limit else text


def _texts(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [_text(v) for v in value if _text(v)]
    return [_text(value)] if _text(value) else []


def _env(env: Any) -> Dict[str, str]:
    env = env if isinstance(env, dict) else {}
    key = _text(env.get("primary")).upper()
    label = _text(env.get("primary_label")) or key
    return {"key": key, "label": label, "short": _ENV_SHORT.get(key, label)} if key or label else {}


def _point(row: Dict[str, Any]) -> Dict[str, Any]:
    purpose = row.get("test_purpose") if isinstance(row.get("test_purpose"), dict) else {}
    config = row.get("key_configuration") if isinstance(row.get("key_configuration"), dict) else {}
    return {
        "id": _text(row.get("row_id")),
        "technique": normalize_technique(row.get("technique"))[0],
        "scenario": _text(row.get("scenario")),
        "purpose": {k: _text(purpose.get(k)) for k in ("with", "when", "then") if _text(purpose.get(k))},
        "config": {_text(k): _text(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in config.items()},
        "pass_criteria": _texts(row.get("pass_criteria")),
        "references": _texts(row.get("references")),
        "env": _env(row.get("test_environment")),
        "cases": [],
    }


def _case(tc: Dict[str, Any], exec_ids: Dict[str, List[str]]) -> Dict[str, Any]:
    tc_id = _text(tc.get("tc_id"))
    return {"id": tc_id, "title": _text(tc.get("title")), "priority": _text(tc.get("priority")),
            "exec_ids": exec_ids.get(tc_id, []), "open_points": len(tc.get("open_points") or [])}


def build_design_map(record: Dict[str, Any]) -> Dict[str, Any]:
    """record 用历史记录 / 导出请求里的字段：requirement_spec、test_design_spec，可选 test_case_spec、executable_cases。"""
    record = record if isinstance(record, dict) else {}
    req_spec = record.get("requirement_spec") if isinstance(record.get("requirement_spec"), dict) else {}
    design = record.get("test_design_spec") if isinstance(record.get("test_design_spec"), dict) else {}
    case_spec = record.get("test_case_spec") if isinstance(record.get("test_case_spec"), dict) else {}
    executable = record.get("executable_cases") if isinstance(record.get("executable_cases"), dict) else {}
    reqs = [r for r in req_spec.get("final_requirements") or [] if isinstance(r, dict)]
    rows = [r for r in design.get("integrated_matrix") or [] if isinstance(r, dict)]
    tcs = [t for t in case_spec.get("testcases") or [] if isinstance(t, dict)]
    objectives = {_text(o.get("objective_id")): o for o in design.get("objectives") or [] if isinstance(o, dict)}
    exec_ids = {_text(t.get("tc_id")): _texts(t.get("exec_case_ids")) for t in executable.get("traceability") or [] if isinstance(t, dict)}

    modules: Dict[str, Dict[str, Any]] = {}
    req_nodes: Dict[str, Dict[str, Any]] = {}

    def req_node(rid: str, req: Dict[str, Any]) -> Dict[str, Any]:
        if rid not in req_nodes:
            level1, level2 = requirement_group(req) if req else (UNGROUPED, rid or UNGROUPED)
            module = modules.setdefault(level1, {"name": level1, "requirements": []})
            req_nodes[rid] = {"id": rid, "name": level2, "title": _text(req.get("title")), "priority": _text(req.get("priority")).upper(),
                              "goal": "", "points": [], "loose_cases": []}
            module["requirements"].append(req_nodes[rid])
        return req_nodes[rid]

    for req in reqs:
        req_node(_text(req.get("req_id")), req)

    points: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        rid = row.get("req_id")
        rid = _text(rid[0] if isinstance(rid, list) and rid else rid)
        node = req_node(rid, {})
        point = _point(row)
        goal = _text((objectives.get(_text(row.get("objective_id"))) or {}).get("goal"))
        node["goal"] = node["goal"] or goal
        node["points"].append(point)
        if point["id"]:
            points.setdefault(point["id"], point)

    for tc in tcs:
        trace = tc.get("trace") if isinstance(tc.get("trace"), dict) else {}
        case = _case(tc, exec_ids)
        owners = [points[r] for r in _texts(trace.get("source_refs")) if r in points]
        if owners:
            for point in owners:
                point["cases"].append(case)
            continue
        rid = next((r for r in _texts(trace.get("req_ids")) if r in req_nodes), "")
        req_node(rid, {})["loose_cases"].append(case)   # 用例没有挂到测试点：按需求归位，评审时能看到

    has_cases = bool(tcs)
    gaps: List[Dict[str, str]] = []
    stats = {"modules": 0, "requirements": 0, "points": 0, "cases": len(tcs),
             "by_technique": {}, "by_env": {}, "by_priority": {}}
    for module in modules.values():
        module["points"] = 0
        for node in module["requirements"]:
            techs = [p["technique"] for p in node["points"]]
            node["techniques"] = {t: techs.count(t) for t in TECHNIQUES if t in techs}
            module["points"] += len(techs)
            stats["requirements"] += 1
            stats["by_priority"][node["priority"] or "未定"] = stats["by_priority"].get(node["priority"] or "未定", 0) + 1
            for p in node["points"]:
                stats["by_technique"][p["technique"]] = stats["by_technique"].get(p["technique"], 0) + 1
                env = p["env"].get("short") or "未定"
                stats["by_env"][env] = stats["by_env"].get(env, 0) + 1
            flags = []
            if not techs:
                flags.append(("no_point", "没有测试点"))
            elif node["priority"] in HIGH_PRIORITIES and set(techs) == {"normal"}:
                flags.append(("normal_only", f"{node['priority']} 需求只设计了正常流程"))
            elif node["priority"] in HIGH_PRIORITIES and len(techs) == 1:
                flags.append(("single_point", f"{node['priority']} 需求只有 1 个测试点"))
            if has_cases:
                missing = [p["id"] for p in node["points"] if not p["cases"]]
                if missing:
                    flags.append(("no_case", "测试点还没有用例：" + "、".join(missing)))
            if node["loose_cases"]:
                flags.append(("loose_case", "有用例没有挂到测试点：" + "、".join(c["id"] for c in node["loose_cases"])))
            node["flags"] = [text for _, text in flags]
            gaps += [{"kind": kind, "module": module["name"], "req_id": node["id"], "name": node["name"], "text": text} for kind, text in flags]
        stats["points"] += module["points"]
    stats["modules"] = len(modules)

    title = _text(record.get("title")) or (_text(reqs[0].get("title")) if reqs else "") or "测试设计"
    return {
        "title": title,
        "generated_at": time.strftime("%Y-%m-%d %H:%M", time.localtime()),
        "has_cases": has_cases,
        "techniques": [{"key": t, "label": TECHNIQUE_LABELS[t]} for t in TECHNIQUES],
        "stats": stats,
        "modules": list(modules.values()),
        "gaps": gaps,
        "design_advice": _texts(design.get("design_advice")),
        "de_scoped": [_text(json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x) for x in design.get("de_scoped") or []],
    }


def render_design_map_html(record: Dict[str, Any]) -> str:
    data = build_design_map(record)
    template = (STATIC_DIR / TEMPLATE_NAME).read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    page_title = data["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return template.replace("__MAP_TITLE__", page_title).replace("/*__MAP_DATA__*/null", payload, 1)
