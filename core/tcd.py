"""3GPP 风格测试用例描述（Test Case Description，TCD）。

结构参照 TS 36.523-1 / 38.523-1 的测试用例写法：
    测试目的 TP（with / when / then）→ 适用性 → 参考条款 → 初始条件（SS / UE / preamble）
    → 关键配置（小区 / 核心网 / UE）→ 特定消息内容（相对默认消息内容的修改）
    → 测试步骤（St、发起方、方向、消息、判定点）→ postamble → 通过标准

TCD 是平台无关但协议信息完整的“中间表示”。四类可执行用例（Artemis / AT Agent / Amarisoft / 协议仪表）
都从它直接投影出草稿，LLM 只需做平台适配，信息不会在环节之间丢失。

为兼容旧页面、旧历史记录和 Excel，规范化后仍保留 preconditions / steps / expected / pass_fail 字段。
"""
import json
import re
from typing import Any, Dict, Iterable, List, Optional

TECHNIQUES = ["normal", "abnormal", "boundary", "timer", "collision", "mobility", "interworking",
              "capability", "performance", "stability"]
TECHNIQUE_LABELS = {
    "normal": "正常流程", "abnormal": "异常/拒绝", "boundary": "边界值", "timer": "定时器",
    "collision": "流程冲突", "mobility": "移动性", "interworking": "互操作/回落", "capability": "能力/配置组合",
    "performance": "性能/KPI", "stability": "长稳/恢复",
}
ACTORS = ["SS", "UE", "TESTER"]

TCD_STEP_SCHEMA = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "step": {"type": ["integer", "string"]},
        "actor": {"type": "string"},
        "action": {"type": "string"},
        "direction": {"type": "string"},
        "layer": {"type": "string"},
        "message": {"type": "string"},
        "msg_ref": {"type": "string"},
        "expected": {"type": "string"},
        "verdict": {"type": ["boolean", "string"]},
        "timing": {"type": "string"},
    },
}

TCD_SCHEMA = {
    "type": "object",
    "required": ["title", "test_purpose", "procedure", "pass_fail", "trace"],
    "properties": {
        "tc_id": {"type": "string"},
        "objective_id": {"type": "string"},
        "title": {"type": "string"},
        "priority": {"type": "string"},
        "technique": {"type": "string"},
        "test_purpose": {
            "type": "object",
            "required": ["when", "then"],
            "properties": {"with": {"type": "string"}, "when": {"type": "string"}, "then": {"type": "string"}},
        },
        "references": {"type": "array", "items": {"type": "string"}},
        "applicability": {"type": "string"},
        "rat": {"type": "string"},
        "test_environment": {"type": "object"},
        "initial_conditions": {"type": "object"},
        "configuration": {"type": "object"},
        "message_contents": {"type": "array", "items": {"type": "object"}},
        "procedure": {"type": "array", "minItems": 1, "items": TCD_STEP_SCHEMA},
        "parameter_variations": {"type": "array", "items": {"type": "object"}},
        "postamble": {"type": "array", "items": {"type": "string"}},
        "pass_fail": {"type": "array", "items": {"type": "string"}},
        "observability": {"type": "object"},
        "trace": {"type": "object", "required": ["req_ids", "source_refs"]},
        "open_points": {"type": "array", "items": {"type": "string"}},
    },
}

TCD_LIST_SCHEMA = {
    "type": "object",
    "required": ["testcases"],
    "properties": {"testcases": {"type": "array", "items": TCD_SCHEMA}},
}

# ---------- 小工具 ----------


def as_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_text_list(value: Any) -> List[str]:
    out = []
    for v in as_list(value):
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        s = str(v).strip()
        if s:
            out.append(s)
    return out


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "yes", "1", "pass", "verdict", "是")


_RRC_HINTS = ("RRC", "SIB", "MIB", "Measurement", "UECapability", "UEInformation", "MobilityFromNR", "MobilityFromEUTRA",
              "DLInformationTransfer", "ULInformationTransfer", "Paging", "CounterCheck", "SystemInformation")
_NAS_HINTS = ("Registration", "Deregistration", "Service", "Authentication", "Identity", "ConfigurationUpdate",
              "Attach", "Detach", "TrackingAreaUpdate", "PDUSession", "PDNConnectivity", "BearerResource", "EPSBearer",
              "DLNASTransport", "ULNASTransport", "Notification", "5GMMStatus", "EMMStatus", "ESMInformation")
_IMS_HINTS = ("SIP", "INVITE", "REGISTER", "PRACK", "BYE", "ACK", "180", "183", "200 OK")


def message_layer(message: str, hint: str = "") -> str:
    if hint:
        return hint.upper()
    m = message or ""
    if any(m.startswith(h) or h in m for h in _IMS_HINTS):
        return "IMS"
    if m.startswith(("RRC", "SIB", "MIB")) or any(h in m for h in _RRC_HINTS):
        return "RRC"
    if any(h in m for h in _NAS_HINTS):
        return "NAS"
    if "MAC" in m or "RAR" in m or "Msg" in m:
        return "MAC"
    return ""


# ---------- 规范化 ----------


def _norm_purpose(raw: Any, fallback_title: str, expected: List[str]) -> Dict[str, str]:
    if isinstance(raw, str):
        raw = {"then": raw}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "with": _text(raw.get("with") or raw.get("given") or raw.get("precondition")),
        "when": _text(raw.get("when") or raw.get("trigger")),
        "then": _text(raw.get("then") or raw.get("ensure_that") or raw.get("expected")) or ("；".join(expected) or fallback_title),
    }


def _norm_ies(raw: Any) -> List[Dict[str, Any]]:
    out = []
    if isinstance(raw, dict):
        raw = [{"path": k, "value": v} for k, v in raw.items()]
    for ie in as_list(raw):
        if not isinstance(ie, dict):
            continue
        path = _text(ie.get("path") or ie.get("ie") or ie.get("name"))
        if not path:
            continue
        out.append({"path": path, "value": ie.get("value"), "note": _text(ie.get("note")), "vary": _text(ie.get("vary"))})
    return out


def _norm_messages(raw: Any) -> List[Dict[str, Any]]:
    out, seen = [], set()
    for idx, m in enumerate(as_list(raw), start=1):
        if not isinstance(m, dict):
            continue
        msg_id = _text(m.get("msg_id") or m.get("id")) or f"M{idx}"
        while msg_id in seen:
            msg_id = f"{msg_id}_{idx}"
        seen.add(msg_id)
        direction = _text(m.get("direction")).upper()
        out.append({
            "msg_id": msg_id,
            "message": _text(m.get("message") or m.get("name")),
            "direction": direction if direction in ("UL", "DL") else ("DL" if not direction else direction),
            "layer": message_layer(_text(m.get("message") or m.get("name")), _text(m.get("layer"))),
            "based_on": _text(m.get("based_on") or m.get("template")) or "默认消息内容",
            "purpose": _text(m.get("purpose")),
            "ies": _norm_ies(m.get("ies")),
        })
    return out


def _norm_steps(raw: Any, legacy_steps: Any = None) -> List[Dict[str, Any]]:
    out = []
    src = as_list(raw)
    if not src and legacy_steps:
        # 旧格式 steps[{action, params}] 也能转成 TCD 步骤
        src = [{"action": s.get("action"), "params": s.get("params") or {}, "actor": "TESTER"}
               for s in as_list(legacy_steps) if isinstance(s, dict)]
    for idx, s in enumerate(src, start=1):
        if isinstance(s, str):
            s = {"action": s}
        if not isinstance(s, dict):
            continue
        message = _text(s.get("message"))
        direction = _text(s.get("direction")).upper().replace("→", "")
        if direction in ("UE->SS", "UESS", "U-S", "U->S"):
            direction = "UL"
        elif direction in ("SS->UE", "SSUE", "S-U", "S->U"):
            direction = "DL"
        actor = _text(s.get("actor")).upper() or ("UE" if direction == "UL" else "SS" if direction == "DL" else "TESTER")
        params = s.get("params")
        if not isinstance(params, dict):
            params = {"value": params} if params not in (None, "", []) else {}
        out.append({
            "step": idx,
            "actor": actor if actor in ACTORS else actor or "TESTER",
            "action": _text(s.get("action")) or ("SEND" if message else "CHECK"),
            "direction": direction if direction in ("UL", "DL") else "",
            "layer": message_layer(message, _text(s.get("layer"))) if message else _text(s.get("layer")).upper(),
            "message": message,
            "msg_ref": _text(s.get("msg_ref") or s.get("config_ref")),
            "params": params,
            "expected": _text(s.get("expected")),
            "verdict": _bool(s.get("verdict")),
            "timing": _text(s.get("timing")),
        })
    return out


def _norm_configuration(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    cells = raw.get("cells")
    if isinstance(cells, dict):
        cells = [cells]
    if not cells and isinstance(raw.get("cell"), dict) and raw["cell"]:
        cells = [raw["cell"]]
    cells = [c for c in as_list(cells) if isinstance(c, dict) and c]
    for i, c in enumerate(cells, start=1):
        c.setdefault("cell_id", f"Cell{i}")
    core = raw.get("core") if isinstance(raw.get("core"), dict) else {}
    ue = raw.get("ue") if isinstance(raw.get("ue"), dict) else {}
    out = {"cells": cells, "core": core, "ue": ue}
    for k, v in raw.items():
        if k not in ("cells", "cell", "core", "ue") and v not in (None, "", [], {}):
            out.setdefault("other", {})[k] = v
    return out


def derive_steps(procedure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """旧格式 steps，供历史页面 / Excel / 兼容下游使用。"""
    steps = []
    for p in procedure:
        params = dict(p.get("params") or {})
        for k in ("actor", "direction", "message", "msg_ref", "expected"):
            if p.get(k):
                params.setdefault(k, p[k])
        steps.append({"action": p.get("action") or "CHECK", "params": params})
    return steps


def normalize_tcd(tc: Dict[str, Any], idx: int = 1) -> Dict[str, Any]:
    pass_fail = as_text_list(tc.get("pass_fail") or tc.get("criteria") or tc.get("pass_criteria"))
    expected = as_text_list(tc.get("expected") or tc.get("expected_results"))
    title = _text(tc.get("title")) or f"测试用例-{idx}"
    procedure = _norm_steps(tc.get("procedure"), tc.get("steps"))
    if procedure and not any(p["verdict"] for p in procedure):
        # 没标判定点时，把带期望结果的最后一步作为判定点
        for p in reversed(procedure):
            if p["expected"]:
                p["verdict"] = True
                break
    ic = tc.get("initial_conditions") if isinstance(tc.get("initial_conditions"), dict) else {}
    legacy_pre = as_text_list(tc.get("preconditions") or tc.get("precondition"))
    initial = {
        "system_simulator": as_text_list(ic.get("system_simulator") or ic.get("ss") or ic.get("network")),
        "ue": as_text_list(ic.get("ue") or ic.get("ue_state")) or legacy_pre,
        "preamble": as_text_list(ic.get("preamble")),
    }
    trace = tc.get("trace") or tc.get("traceability") or {}
    if not isinstance(trace, dict):
        trace = {}
    tags = tc.get("tags") if isinstance(tc.get("tags"), list) else as_text_list(tc.get("tags") or tc.get("labels"))
    technique = _text(tc.get("technique")).lower()
    obs = tc.get("observability") if isinstance(tc.get("observability"), dict) else {}
    out = {
        "tc_id": _text(tc.get("tc_id") or tc.get("testcase_id") or tc.get("id")) or f"TC-{idx:03d}",
        "objective_id": _text(tc.get("objective_id") or tc.get("objectiveId")) or "TO-001",
        "title": title,
        "priority": _text(tc.get("priority")).upper() or next((t for t in tags if str(t).upper() in ("P0", "P1", "P2", "P3")), "P1"),
        "technique": technique if technique in TECHNIQUES else (technique or "normal"),
        "tags": tags or ["Regression"],
        "test_purpose": _norm_purpose(tc.get("test_purpose"), title, expected),
        "references": as_text_list(tc.get("references")),
        "applicability": _text(tc.get("applicability")),
        "rat": _text(tc.get("rat")),
        "test_environment": tc.get("test_environment"),
        "initial_conditions": initial,
        "configuration": _norm_configuration(tc.get("configuration")),
        "message_contents": _norm_messages(tc.get("message_contents") or tc.get("message_configs")),
        "procedure": procedure,
        "parameter_variations": [v for v in as_list(tc.get("parameter_variations")) if isinstance(v, dict)],
        "postamble": as_text_list(tc.get("postamble")),
        "expected": expected or [p["expected"] for p in procedure if p["verdict"] and p["expected"]] or ["待补充期望结果"],
        "pass_fail": pass_fail or ["待补充通过条件"],
        "observability": {
            "must_capture": as_text_list(obs.get("must_capture") or obs.get("logs")) or ["modem_log"],
            "assertions": as_text_list(obs.get("assertions")),
        },
        "failure_taxonomy": [f for f in as_list(tc.get("failure_taxonomy")) if isinstance(f, dict)],
        "trace": {
            "req_ids": as_text_list(trace.get("req_ids") or trace.get("requirements")),
            "source_refs": as_text_list(trace.get("source_refs") or trace.get("row_ids") or trace.get("sources")) or ["USER_INPUT"],
        },
        "requirement_configs": [c for c in as_list(tc.get("requirement_configs")) if isinstance(c, dict)],
        "open_points": as_text_list(tc.get("open_points")),
    }
    out["preconditions"] = initial["ue"] + initial["preamble"] or ["待补充前置条件"]
    out["steps"] = derive_steps(procedure)
    return out


def purpose_text(tc: Dict[str, Any]) -> str:
    tp = tc.get("test_purpose") or {}
    parts = []
    if tp.get("with"):
        parts.append(f"with {{ {tp['with']} }}")
    body = []
    if tp.get("when"):
        body.append(f"when {{ {tp['when']} }}")
    if tp.get("then"):
        body.append(f"then {{ {tp['then']} }}")
    if body:
        parts.append("ensure that { " + " ".join(body) + " }")
    return " ".join(parts)


def config_blob_fields(tc: Dict[str, Any]) -> Dict[str, Any]:
    return {k: tc.get(k) for k in ("configuration", "message_contents", "procedure", "parameter_variations", "initial_conditions")}


# ---------- 需求配置补入（确定性，不依赖 LLM） ----------


def patch_explicit_configs(tc: Dict[str, Any], configs: List[Dict[str, Any]], present) -> List[Dict[str, Any]]:
    """需求写明但 TCD 里没出现的配置，按 target 补到 configuration / message_contents。返回逐项落地情况。"""
    from utils.req_configs import blob_of  # 避免循环引用

    results = []
    for c in configs:
        blob = blob_of(config_blob_fields(tc), ["configuration", "message_contents", "procedure", "parameter_variations",
                                                "initial_conditions"])
        status = "applied"
        if not present(c["value"], blob):
            status = "patched"
            name, target = c.get("name") or "param", c.get("target") or ""
            cfg = tc["configuration"]
            if target == "cell":
                if not cfg["cells"]:
                    cfg["cells"].append({"cell_id": "Cell1"})
                cfg["cells"][0].setdefault(name, c["value"])
            elif target == "core":
                cfg["core"].setdefault(name, c["value"])
            elif target == "message":
                msgs = tc["message_contents"]
                holder = next((m for m in msgs if m.get("msg_id") == "M-REQ"), None)
                if holder is None:
                    holder = {"msg_id": "M-REQ", "message": "", "direction": "DL", "layer": c.get("layer", ""),
                              "based_on": "默认消息内容", "purpose": "需求写明的消息字段（所属消息待确认）", "ies": []}
                    msgs.append(holder)
                holder["ies"].append({"path": name, "value": c["value"], "note": c.get("source_text", ""), "vary": ""})
            elif target == "ue":
                cfg["ue"].setdefault(name, c["value"])
            else:
                cfg.setdefault("other", {}).setdefault(name, c["value"])
        results.append({"req_id": c.get("req_id", ""), "name": c.get("name", ""), "value": c.get("value"),
                        "target": c.get("target", ""), "source_text": c.get("source_text", ""), "status": status})
    tc["requirement_configs"] = results
    return [r for r in results if r["status"] == "patched"]


# ---------- 投影到各执行平台的草稿 ----------


def _cell_config(tc: Dict[str, Any]) -> Dict[str, Any]:
    cfg = tc.get("configuration") or {}
    cells = cfg.get("cells") or []
    out: Dict[str, Any] = {}
    if len(cells) == 1:
        out = {k: v for k, v in cells[0].items() if k != "cell_id"}
    elif cells:
        out = {"cells": cells}
    other = cfg.get("other") or {}
    for k, v in other.items():
        out.setdefault(k, v)
    return out


def _steps_with_messages(tc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [p for p in tc.get("procedure") or [] if p.get("message")]


def _msg_by_id(tc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {m["msg_id"]: m for m in tc.get("message_contents") or []}


def _ies_dict(msg: Optional[Dict[str, Any]], limit: int = 8) -> Dict[str, Any]:
    if not msg:
        return {}
    return {ie["path"]: ie.get("value") for ie in (msg.get("ies") or [])[:limit]}


def _procedure_lines(tc: Dict[str, Any]) -> List[str]:
    lines = []
    for p in tc.get("procedure") or []:
        head = p.get("action") or ""
        if p.get("message"):
            arrow = "UE→网络" if p.get("direction") == "UL" else "网络→UE" if p.get("direction") == "DL" else ""
            head = f"{head} {p['message']}" + (f"（{arrow}）" if arrow else "")
        params = p.get("params") or {}
        if params:
            head += "，" + "，".join(f"{k}={_text(v)}" for k, v in params.items())
        if p.get("expected"):
            head += f"；期望：{p['expected']}"
        lines.append(f"{p.get('step')}. {head.strip()}")
    return lines


def to_amarisoft(tc: Dict[str, Any]) -> Dict[str, Any]:
    msgs = _msg_by_id(tc)
    ic = tc.get("initial_conditions") or {}
    key_params = [{"name": v.get("name", ""), "values": v.get("values"), "layer": v.get("layer", ""),
                   "purpose": v.get("purpose", "")} for v in tc.get("parameter_variations") or []]
    for k, v in ((tc.get("configuration") or {}).get("ue") or {}).items():
        key_params.append({"name": k, "value": v, "layer": "UE", "purpose": "UE 侧配置"})
    return {
        "source_tc_id": tc.get("tc_id", ""),
        "title": tc.get("title", ""),
        "objective": purpose_text(tc) or tc.get("title", ""),
        "test_purpose": tc.get("test_purpose"),
        "technique": tc.get("technique", ""),
        "rat": tc.get("rat", ""),
        "ue_preconditions": (ic.get("ue") or []) + (ic.get("preamble") or []),
        "cell_config": _cell_config(tc),
        "core_config": dict((tc.get("configuration") or {}).get("core") or {}),
        "key_parameters": key_params,
        "procedure": [{"step": p["step"], "action": p.get("action", ""),
                       "params": {**(p.get("params") or {}), **({"message": p["message"], "direction": p["direction"]} if p.get("message") else {})},
                       "expected": p.get("expected", ""), "verdict": bool(p.get("verdict"))}
                      for p in tc.get("procedure") or []],
        "expected_signaling": [{"layer": p.get("layer") or message_layer(p["message"]), "direction": p.get("direction", ""),
                                "message": p["message"], "key_ies": _ies_dict(msgs.get(p.get("msg_ref", "")))}
                               for p in _steps_with_messages(tc)],
        "message_configs": [{"message": m["message"], "direction": m["direction"], "ies": m["ies"]}
                            for m in tc.get("message_contents") or [] if m.get("ies")],
        "pass_criteria": list(tc.get("pass_fail") or []),
        "logs_to_capture": list((tc.get("observability") or {}).get("must_capture") or []),
        "references": list(tc.get("references") or []),
        "open_points": list(tc.get("open_points") or []),
    }


def to_protocol(tc: Dict[str, Any]) -> Dict[str, Any]:
    msgs = _msg_by_id(tc)
    flow = []
    for i, p in enumerate(_steps_with_messages(tc), start=1):
        ref = p.get("msg_ref", "") if p.get("msg_ref", "") in msgs else ""
        flow.append({"seq": i, "direction": p.get("direction", ""), "layer": p.get("layer") or message_layer(p["message"]),
                     "message": p["message"], "config_ref": ref, "key_ies": {} if ref else dict(p.get("params") or {}),
                     "timing": p.get("timing", ""), "note": p.get("expected", "")})
    layers = sorted({f["layer"] for f in flow if f["layer"]} | {m["layer"] for m in msgs.values() if m.get("layer")})
    tp = tc.get("test_purpose") or {}
    ic = tc.get("initial_conditions") or {}
    return {
        "source_tc_id": tc.get("tc_id", ""),
        "title": tc.get("title", ""),
        "scenario": "；".join(x for x in (tp.get("when"), tp.get("then")) if x) or tc.get("title", ""),
        "test_purpose": tc.get("test_purpose"),
        "technique": tc.get("technique", ""),
        "layers": layers,
        "rat": tc.get("rat", ""),
        "preconditions": (ic.get("ue") or []) + (ic.get("preamble") or []),
        "cell_config": _cell_config(tc),
        "core_config": dict((tc.get("configuration") or {}).get("core") or {}),
        "message_configs": [{"msg_id": m["msg_id"], "message": m["message"], "template": m["message"] or m.get("based_on", ""),
                             "direction": m["direction"], "purpose": m.get("purpose", ""), "ies": m["ies"]}
                            for m in tc.get("message_contents") or []],
        "signaling_flow": flow,
        "parameter_variations": [{"name": v.get("name", ""), "values": v.get("values"), "purpose": v.get("purpose", "")}
                                 for v in tc.get("parameter_variations") or []],
        "checkpoints": [{"item": f"St{p['step']} {p.get('message') or p.get('action', '')}".strip(), "expected": p.get("expected", "")}
                        for p in tc.get("procedure") or [] if p.get("verdict")],
        "pass_criteria": list(tc.get("pass_fail") or []),
        "references": list(tc.get("references") or []),
        "open_points": list(tc.get("open_points") or []),
    }


def to_live(tc: Dict[str, Any]) -> Dict[str, Any]:
    """实网（Artemis / AT Agent）草稿：按步骤拼成自然语言 goal。"""
    ic = tc.get("initial_conditions") or {}
    goal_lines = [tc.get("title", "")] + _procedure_lines(tc)
    return {
        "source_tc_id": tc.get("tc_id", ""),
        "title": tc.get("title", ""),
        "goal": "\n".join(x for x in goal_lines if x),
        "expected_result": "；".join(tc.get("pass_fail") or tc.get("expected") or []),
        "preconditions": "；".join((ic.get("ue") or []) + (ic.get("preamble") or [])),
        "group": "",
        "priority": tc.get("priority") if tc.get("priority") in ("P0", "P1", "P2") else "P1",
        "redline": tc.get("priority") == "P0",
    }


def project(route: str, tc: Dict[str, Any]) -> Dict[str, Any]:
    tc = normalize_tcd(tc) if "procedure" not in tc or "configuration" not in tc else tc
    if route == "amarisoft":
        return to_amarisoft(tc)
    if route == "protocol":
        return to_protocol(tc)
    return to_live(tc)


def summarize_for_prompt(tc: Dict[str, Any]) -> Dict[str, Any]:
    """给可执行用例 LLM 的 TCD 视图：去掉兼容字段，控制长度。"""
    keys = ["tc_id", "title", "priority", "technique", "test_purpose", "references", "applicability", "rat",
            "test_environment", "initial_conditions", "configuration", "message_contents", "procedure",
            "parameter_variations", "postamble", "pass_fail", "observability", "trace", "open_points"]
    out = {k: tc.get(k) for k in keys if tc.get(k) not in (None, "", [], {})}
    if "procedure" not in out and tc.get("steps"):
        out["steps"] = tc["steps"]
    return out


def iter_messages(tcs: Iterable[Dict[str, Any]]) -> Iterable[str]:
    for tc in tcs:
        for p in tc.get("procedure") or []:
            if p.get("message"):
                yield p["message"]


_TC_NUM = re.compile(r"(\d+)$")


def renumber(tcs: List[Dict[str, Any]], row_order: List[str]) -> List[Dict[str, Any]]:
    """按矩阵行顺序重排并统一编号（并行批次各自从 TC-001 开始会撞号）。"""
    pos = {rid: i for i, rid in enumerate(row_order)}

    def key(item):
        i, tc = item
        refs = tc.get("trace", {}).get("source_refs") or []
        return (min([pos.get(r, len(pos)) for r in refs] or [len(pos)]), i)

    ordered = [tc for _, tc in sorted(enumerate(tcs), key=key)]
    for n, tc in enumerate(ordered, start=1):
        tc["tc_id"] = f"TC-{n:03d}"
    return ordered
