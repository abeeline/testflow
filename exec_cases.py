"""把测试用例（3GPP 风格 TCD）落地为各执行平台可直接使用的 JSON case。

做法：先由 TCD 确定性投影出各平台草稿（core/tcd.py: project），草稿已包含 TCD 的全部配置、消息内容和步骤；
再交给各路线 LLM 做平台适配（Amarisoft 动作、仪表消息模板、自然语言 goal / AT 指令），
LLM 结果缺的字段用草稿补齐，LLM 不可用时直接用草稿，所以信息不会在这一步丢失。

每条测试用例按验收方案分流到四条路线：
- artemis:   手机实网系统测试，导出 Artemis 用例库格式（artemis-case-library v1, profile=flash）
- at_agent:  模组 AT 实网测试，导出 AT Agent 用例库格式（artemis-case-library v1, profile=at）
- amarisoft: Amarisoft 模拟基站，导出给 Amarisoft Agent 的 case（关键 PHY/协议参数 + 步骤 + 期望信令）
- protocol:  协议分析仪 / 仿真仪表，导出协议流程测试需求（关键消息模板 + IE 覆盖值、信令流程、检查点），供 PRTest 后续落地
"""
import asyncio
import copy
import datetime as dt
import json
import uuid
from typing import Any, Dict, List

from pocketflow import AsyncNode
from core.events import emit
from core.grouping import ensure_suite, suite_tree
from core.llm import generate_json, run_split_on_truncate
from core.quality import uncovered_thresholds
from core.tcd import normalize_tcd, owner_message, project, summarize_for_prompt
from utils.paths import prompt_path
from utils.req_configs import (blob_of, config_status, extract_config_lines, name_key, normalize_explicit_configs,
                               value_present, value_tokens)

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

# 每次 LLM 调用处理的用例数。协议需求要逐条展开消息 IE，输出很长，分小批并行生成。
ROUTE_BATCH_SIZE = {"artemis": 6, "at_agent": 6, "amarisoft": 3, "protocol": 2}

# 各路线 item 至少要有的字段，缺了就让 LLM 重试。
ROUTE_ITEM_REQUIRED = {
    "amarisoft": ["source_tc_id", "cell_config", "procedure"],
    "protocol": ["source_tc_id", "message_configs", "signaling_flow"],
}

# 基站/仪表路线要逐项核对“需求写明的配置”是否落到了这些字段里。
CONFIG_ROUTES = ("amarisoft", "protocol")
ROUTE_CONFIG_FIELDS = {
    "amarisoft": ["cell_config", "core_config", "key_parameters", "message_configs", "procedure", "expected_signaling"],
    "protocol": ["cell_config", "core_config", "ue_config", "test_parameters", "message_configs", "procedure", "signaling_flow",
                 "parameter_variations", "checkpoints"],
}

# 写进 bundle 的字段说明，方便下游 Agent 不看文档也能理解每个字段。
FIELD_GUIDE = {
    "amarisoft": {
        "source_tc_id": "来源测试用例编号",
        "test_purpose": "3GPP 测试目的：with（初始状态）/ when（触发）/ then（期望行为）",
        "technique": "测试技术：normal / abnormal / boundary / timer / collision / mobility / interworking / capability / performance / stability",
        "rat": "制式：LTE / NR_SA / NR_NSA / NB-IoT / LTE-M / NR_NTN",
        "ue_preconditions": "UE 初始状态与前置流程（preamble）",
        "cell_config": "小区/PHY 关键参数（band、dl_arfcn/ssb_arfcn、bandwidth_mhz、scs_khz、tdd_pattern、plmn、tac、cell_id、功率、SIB 字段等），按此生成 enb/gnb 配置",
        "core_config": "核心网/NAS 参数（注册接受/拒绝及 cause、T3412/T3512/T3324 等定时器、PSM/eDRX、APN/DNN、IMS、鉴权），按此生成 mme 配置",
        "key_parameters": "本用例要验证或扫描的关键参数：name、value 或 values、layer、purpose；各取值的前置或预期不同时用 variants 逐个列出",
        "message_configs": "需要定制的 RRC/NAS 消息：msg_id、message、direction、purpose、ies[{path, value, note}]，path 为 ASN.1 字段路径",
        "procedure": "有序步骤：step、actor（SS=基站侧，UE=被测终端，TESTER=终端侧操作）、action（英文动作名）、params（具体取值，含 message/direction）、"
                     "expected、verdict（是否判定点）、timing（时序/定时器约束，可无）、msg_ref（引用 message_configs 的 msg_id，可无）",
        "expected_signaling": "期望信令序列：layer、direction、message、key_ies",
        "pass_criteria": "通过标准（保留原用例数值门限）",
        "references": "3GPP 规范条款",
        "requirement_configs": "需求原文写明的配置及落地情况：status=applied 已落到上面字段，patched 生成结果里没有、已按需求原值补入（applied_to 写明补到哪），not_applicable 不适用（note 说明），conflict 与规范冲突（仍按需求值）",
        "open_points": "执行前仍需确认的问题",
    },
    "protocol": {
        "source_tc_id": "来源测试用例编号",
        "test_purpose": "3GPP 测试目的：with（初始状态）/ when（触发）/ then（期望行为）",
        "technique": "测试技术：normal / abnormal / boundary / timer / collision / mobility / interworking / capability / performance / stability",
        "layers": "被测协议层",
        "preconditions": "进入被测流程前 UE 状态",
        "cell_config": "仪表侧小区基础配置",
        "core_config": "仪表侧核心网/NAS 配置（注册接受/拒绝及 cause、NAS 定时器、APN/DNN 等）",
        "ue_config": "UE 侧设置和 UE 本地行为参数（如 UE 侧 NAS 定时器取值），不是仪表下发的消息内容",
        "test_parameters": "需求写明、但不属于小区 / 核心网 / UE / 某条消息的测试参数（门限、次数等）",
        "procedure": "完整的有序步骤，执行以它为准：step、actor（SS=仪表侧，UE=被测终端，TESTER=终端侧操作）、action（英文动作名）、params、"
                     "expected、verdict（是否判定点）、timing、msg_ref。改位置、改功率、注入故障、等待、恢复这类非消息动作只出现在这里",
        "message_configs": "仪表要下发/校验的关键消息：msg_id、message、template、direction、ies[{path, value, note, vary}]，path 为 ASN.1 字段路径，按此写消息模板 XML 覆盖值",
        "signaling_flow": "procedure 中信令步骤的视图：seq、step（对应 procedure 的步骤号）、direction、layer、message、config_ref（引用 msg_id）、key_ies、timing",
        "parameter_variations": "需要扫描的参数，name 对应 ies[].vary；各取值的前置或预期不同时用 variants 逐个列出（id、value、preconditions、expected）",
        "checkpoints": "逐项检查点",
        "requirement_configs": "需求原文写明的配置及落地情况：status=applied 已落到上面字段，patched 生成结果里没有、已按需求原值补入（applied_to 写明补到哪），not_applicable 不适用（note 说明），conflict 与规范冲突（仍按需求值），missing 没有落地且无法确定该放在哪（见 open_points）",
        "references": "3GPP 规范条款",
        "open_points": "落地前仍需确认的问题",
    },
}
SOURCE_LINES_NOTE = ("需求原文中的配置行（原样摘录）。status：covered=取值都已出现在本文件的 case 中，partial=部分出现，"
                     "other_route=不在本文件、但已出现在其他执行平台的用例中（见 found_in），not_found=所有平台的用例里都没有，请人工确认是否遗漏")

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
    if "AT+" in blob or "AT指令" in blob or any(
            str(p.get("action") or "").upper().startswith("AT_") for p in tc.get("procedure") or [] if isinstance(p, dict)):
        return "at_agent"
    forms = _form_factors(product_profile)
    if forms & MODULE_FORM_FACTORS and not forms & PHONE_FORM_FACTORS:
        return "at_agent"
    return "artemis"


def _tc_summary(tc: Dict[str, Any]) -> Dict[str, Any]:
    """只给 LLM 必要字段（TCD 视图），控制提示词长度。"""
    return summarize_for_prompt(tc)


def _requirement_index(requirement_spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for r in (requirement_spec or {}).get("final_requirements", []) or []:
        if isinstance(r, dict) and r.get("req_id"):
            out[str(r["req_id"])] = r
    return out


def _requirement_view(req: Dict[str, Any]) -> Dict[str, Any]:
    """给可执行用例 LLM 的需求视图：标题 + 预期/验收/约束 + 需求写明的配置。"""
    view = {k: req.get(k) for k in ("req_id", "title", "preconditions", "trigger", "expected", "constraints") if req.get(k)}
    acc = req.get("acceptance") or {}
    if isinstance(acc, dict) and (acc.get("pass_fail") or acc.get("kpi")):
        view["acceptance"] = {k: acc.get(k) for k in ("pass_fail", "kpi") if acc.get(k)}
    configs = normalize_explicit_configs(req)
    if configs:
        view["explicit_configs"] = [{k: v for k, v in c.items() if k != "req_id"} for c in configs]
    return view


def _linked_configs(tc: Dict[str, Any], req_index: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for rid in (tc.get("trace") or {}).get("req_ids") or []:
        req = req_index.get(str(rid))
        if req:
            out.extend(normalize_explicit_configs(req))
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
    for v in [llm_value, tc.get("priority"), *(tc.get("tags") or [])]:
        s = str(v or "").upper()
        if s in ("P0", "P1", "P2"):
            return s
    return "P1"


def _merge_message_configs(item: Dict[str, Any], draft: Dict[str, Any]) -> None:
    """TCD 里写明的消息 IE 是上游定下来的内容：LLM 适配时漏掉的消息 / IE 按草稿补回，已有的不动。"""
    mine = [m for m in item.get("message_configs") or [] if isinstance(m, dict)]
    used_ids = {str(m.get("msg_id") or "") for m in mine}
    for dm in draft.get("message_configs") or []:
        name = str(dm.get("message") or "").strip().lower()
        target = next((m for m in mine if name and str(m.get("message") or "").strip().lower() == name
                       and str(m.get("direction") or dm.get("direction")) == str(dm.get("direction"))), None)
        if target is None:
            extra = dict(dm)
            if extra.get("msg_id") and extra["msg_id"] in used_ids:
                extra["msg_id"] = f"{extra['msg_id']}-TCD"
            used_ids.add(str(extra.get("msg_id") or ""))
            mine.append(extra)
            continue
        ies = target.setdefault("ies", [])
        if not isinstance(ies, list):
            continue
        have = {name_key(str(ie.get("path") or "").split(".")[-1]) for ie in ies if isinstance(ie, dict)}
        blob = blob_of({"ies": ies}, ["ies"])
        for ie in dm.get("ies") or []:
            if name_key(str(ie.get("path") or "").split(".")[-1]) in have or (
                    len(str(ie.get("value") or "")) >= 3 and value_present(ie.get("value"), blob)):
                continue
            ies.append({**ie, "note": "；".join(x for x in (ie.get("note"), "来自测试用例，适配时遗漏已补回") if x)})
    if mine:
        item["message_configs"] = mine


def _merge_with_draft(route: str, item: Dict[str, Any], draft: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 输出缺的或空的字段用草稿补齐（草稿来自 TCD，信息完整）。"""
    for k, v in draft.items():
        if k.startswith("_"):
            continue
        if route == "protocol" and k == "procedure" and v:
            item[k] = v  # 有序步骤以用例为准：适配只补平台细节，不能增删或调换步骤
            continue
        cur = item.get(k)
        if cur in (None, "", [], {}):
            item[k] = v
        elif isinstance(cur, dict) and isinstance(v, dict):
            for dk, dv in v.items():  # 小区/核心网配置：草稿里有、LLM 漏掉的键补回
                cur.setdefault(dk, dv)
    if route in CONFIG_ROUTES:
        _merge_message_configs(item, draft)
    return item


# ---------- 需求配置落地校验（基站 / 仪表路线） ----------

def _fill_config(route: str, item: Dict[str, Any], c: Dict[str, Any], clash: bool) -> str:
    """把一项需求配置按 target 放进 case，返回落到的字段路径。clash 表示已有同名但取值不同的项，需求值另存不覆盖。"""
    name = c["name"] or "param"
    key = f"{name}（需求值）" if clash else name
    target = c.get("target") or ""
    if target in ("cell", "core"):
        field = f"{target}_config"
        if not isinstance(item.get(field), dict):
            item[field] = {}
        item[field][key] = c["value"]
        return f"{field}.{key}"
    if target == "message":
        # 只补进需求原文点了名的那条消息；找不到就不补，交给人确认。
        # 不能塞进第一条消息：方向和所属容器都可能是错的，执行方照着构造就是一条错误的消息。
        holder = owner_message(item.get("message_configs") or [], c)
        if holder is None:
            return ""
        holder.setdefault("ies", []).append({"path": key, "value": c["value"], "note": c.get("source_text", ""), "vary": ""})
        return f"message_configs.{holder.get('msg_id', '')}"
    if route == "amarisoft":
        item.setdefault("key_parameters", []).append(
            {"name": name, "value": c["value"], "layer": c.get("layer", ""), "purpose": "需求写明的配置"})
        return "key_parameters"
    field = "ue_config" if target == "ue" else "test_parameters"
    if not isinstance(item.get(field), dict):
        item[field] = {}
    item[field][key] = c["value"]
    return f"{field}.{key}"


def _match_llm_entry(cfg: Dict[str, Any], entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    name = str(cfg.get("name") or "").strip().lower()
    value = str(cfg.get("value") or "").strip().lower()
    for e in entries:
        if name and str(e.get("name") or "").strip().lower() == name and (
                not value or str(e.get("value") or "").strip().lower() in (value, "")):
            return e
    for e in entries:
        if value and str(e.get("value") or "").strip().lower() == value:
            return e
    return {}


def apply_requirement_configs(route: str, item: Dict[str, Any], configs: List[Dict[str, Any]]) -> List[str]:
    """核对需求写明的配置是否落到了 case 的配置字段里，没落的按需求原值补进去。
    逐项结果写到 item.requirement_configs，返回被补入的项（用于告警）。"""
    llm_entries = [e for e in (item.get("requirement_configs") or []) if isinstance(e, dict)]
    fields = ROUTE_CONFIG_FIELDS[route]
    results, patched, used, unplaced = [], [], set(), []
    for c in configs:
        e = _match_llm_entry(c, llm_entries)
        if e:
            used.add(id(e))
        llm_status = str(e.get("status") or "").strip().lower()
        note, applied_to = str(e.get("note") or ""), e.get("applied_to", "")
        st = config_status(c, item, fields)
        if st["status"] == "applied":
            status = "conflict" if llm_status == "conflict" else "applied"
        elif llm_status == "not_applicable":
            status = "not_applicable"
        else:
            applied_to = _fill_config(route, item, c, clash=st["status"] == "conflict")
            if applied_to:
                status = "patched"
                note = "生成结果中未出现，已按需求原值补入" + (
                    f"（case 中同名项为 {_text(st['found'][0])}，未覆盖，请确认）" if st["found"] else "")
                patched.append(f"{c['name']}={c['value']}")
            else:
                status = "missing"
                note = "生成结果中未出现，也无法确定它属于哪条消息，没有自动补入"
                unplaced.append(f"需求配置未落地：{c['name']}={c['value']}，无法确定它属于哪条消息（需求原文：{str(c.get('source_text') or '')[:80]}），请确认应放在哪里")
        results.append({
            "req_id": c.get("req_id", ""), "name": c["name"], "value": c["value"], "layer": c.get("layer", ""),
            "target": c.get("target", ""), "source_text": c.get("source_text", ""),
            "applied_to": applied_to, "status": status, "note": note,
        })
    # LLM 自己从原文配置行补充的条目也保留，同样核对一次
    blob = blob_of(item, fields)
    for e in llm_entries:
        if id(e) in used:
            continue
        status = str(e.get("status") or "").strip().lower() or "applied"
        if status == "applied" and not value_present(e.get("value"), blob):
            status = "missing"
        results.append({**e, "status": status})
    item["requirement_configs"] = results
    clashes = [r for r in results if r["status"] == "patched" and "同名项" in r["note"]]
    if clashes or unplaced:
        ops = item.setdefault("open_points", [])
        if not isinstance(ops, list):
            ops = item["open_points"] = [str(ops)]
        ops.extend(f"需求配置待确认：{r['name']}={r['value']}，{r['note']}" for r in clashes)
        ops.extend(x for x in unplaced if x not in ops)
    return patched


def source_lines_coverage(lines: List[Dict[str, Any]], items: List[Dict[str, Any]], route: str) -> List[Dict[str, Any]]:
    """原文配置行逐条核对：取值是否出现在本路线的任一 case 里。"""
    blob = "".join(blob_of(it, ROUTE_CONFIG_FIELDS[route]) for it in items)
    out = []
    for line in lines:
        vals = line.get("values") or value_tokens(line["text"])
        hit = [v for v in vals if value_present(v, blob)]
        status = "covered" if vals and len(hit) == len(vals) else ("partial" if hit else "not_found")
        out.append({"line_id": line["line_id"], **({"req_id": line["req_id"]} if line.get("req_id") else {}),
                    "text": line["text"], "values": vals, "matched_values": hit, "status": status})
    return out


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
        "group": _cut(item.get("group") or " / ".join(x for x in ((tc.get("suite") or {}).get("level1"), (tc.get("suite") or {}).get("level2")) if x), _GROUP_MAX),
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
                 req_index: Dict[str, Dict[str, Any]], bug_ids: List[str],
                 source_lines: List[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                 "suite": ensure_suite(tc, req_index), "trace": _trace_for(tc, req_index, bug_ids)}
        out_items.append(entry)
    suites = suite_tree(out_items)
    source = {"note": SOURCE_LINES_NOTE, "config_lines": source_lines_coverage(source_lines or [], out_items, route)}
    if route == "amarisoft":
        # v4：新增 suites（两级用例分组）和每条 case 的 suite
        # v3：新增 test_purpose、technique、references、procedure[].verdict（来自 3GPP TCD）；v2 起有 message_configs、requirement_configs
        return {"format": "testflow-amarisoft-case", "version": 4, "exported_at": exported_at,
                "field_guide": FIELD_GUIDE["amarisoft"], "source_requirement": source, "suites": suites, "cases": out_items}
    # v6：新增 procedure（完整有序步骤，含非消息动作）、ue_config、test_parameters；signaling_flow / checkpoints 带 step
    # v5：新增 suites（两级用例分组）和每条的 suite
    # v4：新增 test_purpose、technique（来自 3GPP TCD）；v3 起有 requirement_configs、source_requirement、field_guide
    return {"format": "testflow-protocol-test-requirement", "version": 6, "exported_at": exported_at,
            "field_guide": FIELD_GUIDE["protocol"], "source_requirement": source, "suites": suites, "items": out_items}


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
            "suite": ensure_suite(tc, req_index),
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
        emit(shared, "node_running", {"node": "ExecutableCaseNode", "label": "生成可执行用例"})
        # 旧历史记录里的用例（steps 格式）也先转成 TCD
        tcs = [tc if "procedure" in tc and "configuration" in tc else normalize_tcd(tc, i)
               for i, tc in enumerate((shared.get("test_case_spec") or {}).get("testcases", []), start=1) if isinstance(tc, dict)]
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
        source_lines = extract_config_lines(shared.get("input_requirements") or [])
        meta = shared.get("requirement_meta") or []
        if len(meta) == len(shared.get("input_requirements") or []):  # 导入的需求清单：标出每行原文属于哪条需求
            for line in source_lines:
                line["req_id"] = str((meta[line["req_no"] - 1] or {}).get("req_id") or "")

        groups: Dict[str, List[Dict[str, Any]]] = {r: [] for r in ROUTES}
        for tc in tcs:
            groups[routes[str(tc.get("tc_id") or "")]].append(tc)

        for r in ROUTES:
            text = prompt_path(ROUTE_PROMPTS[r]).read_text(encoding="utf-8") if groups[r] else ""
            missing_vars = [v for v in ("{draft_json}",) + (("{requirement_configs_json}",) if r in CONFIG_ROUTES else ())
                            if groups[r] and v not in text]
            if missing_vars:
                shared.setdefault("warnings", []).append(
                    f"ExecutableCaseNode-{r}: 当前提示词缺少 {'、'.join(missing_vars)}（可能是旧版自定义模板），"
                    "结果只做事后补齐；建议在 Prompt Settings 恢复默认模板")

        def _schema(route: str) -> Dict[str, Any]:
            list_key = ROUTE_LIST_KEY[route]
            item_schema: Dict[str, Any] = {"type": "object", "required": ["source_tc_id"]}
            if route in ROUTE_ITEM_REQUIRED:
                item_schema = {"type": "object", "required": ROUTE_ITEM_REQUIRED[route],
                               "properties": {"message_configs": {"type": "array"}, "signaling_flow": {"type": "array"},
                                              "cell_config": {"type": "object"}, "procedure": {"type": "array"},
                                              "requirement_configs": {"type": "array"}}}
            return {"type": "object", "required": [list_key], "properties": {list_key: {"type": "array", "items": item_schema}}}

        drafts = {str(tc.get("tc_id") or ""): project(routes[str(tc.get("tc_id") or "")], tc) for tc in tcs}

        async def llm_batch(route: str, batch_tcs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            list_key = ROUTE_LIST_KEY[route]
            rids = list(dict.fromkeys(str(r) for tc in batch_tcs for r in (tc.get("trace") or {}).get("req_ids") or []))
            data = await asyncio.to_thread(  # 并发上限由 core.llm 统一控制
                generate_json,
                shared=shared,
                template_name=ROUTE_PROMPTS[route],
                variables={
                    "testcases_json": json.dumps([_tc_summary(tc) for tc in batch_tcs], ensure_ascii=False),
                    "draft_json": json.dumps([drafts[str(tc.get("tc_id") or "")] for tc in batch_tcs], ensure_ascii=False),
                    "requirements_json": json.dumps([_requirement_view(req_index[r]) for r in rids if r in req_index],
                                                    ensure_ascii=False),
                    "product_profile_json": json.dumps(prep_res["product_profile"].get("selected", {}), ensure_ascii=False),
                    "requirement_configs_json": json.dumps(
                        {"per_testcase": {str(tc.get("tc_id") or ""): _linked_configs(tc, req_index) for tc in batch_tcs},
                         "source_config_lines": [{"line_id": x["line_id"], "text": x["text"]} for x in source_lines]},
                        ensure_ascii=False),
                },
                schema=_schema(route),
                warn_tag=f"ExecutableCaseNode-{route}",
                raise_on_truncate=len(batch_tcs) > 1,
            )
            return [x for x in data.get(list_key, []) if isinstance(x, dict)]

        async def run_batch(route: str, batch_tcs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            items: List[Dict[str, Any]] = []
            used_llm = False
            if shared["llm_client"].enabled:
                try:
                    parts = await run_split_on_truncate(batch_tcs, lambda b: llm_batch(route, b))
                    items = [x for part in parts for x in part]
                    used_llm = True
                except Exception as exc:
                    shared.setdefault("warnings", []).append(f"ExecutableCaseNode-{route}: LLM 适配失败，使用由用例直接映射的草稿: {exc}")
            elif batch_tcs:
                shared.setdefault("warnings", []).append(f"ExecutableCaseNode-{route}: LLM未配置，使用由用例直接映射的草稿")
            tcs_by_id = {str(tc.get("tc_id") or ""): tc for tc in batch_tcs}
            # LLM 结果缺的字段用 TCD 草稿补齐
            for it in items:
                tc_id = str(it.get("source_tc_id") or "")
                if tc_id in tcs_by_id:
                    _merge_with_draft(route, it, copy.deepcopy(drafts[tc_id]))
            covered = {str(x.get("source_tc_id") or "") for x in items}
            missing = [tc for tc in batch_tcs if str(tc.get("tc_id") or "") not in covered]
            if missing and used_llm:
                shared.setdefault("warnings", []).append(
                    f"ExecutableCaseNode-{route}: {len(missing)} 条用例未被 LLM 覆盖，已用由用例直接映射的草稿补齐")
            items.extend(copy.deepcopy(drafts[str(tc.get("tc_id") or "")]) for tc in missing)
            if route in CONFIG_ROUTES:
                patched = 0
                for it in items:
                    configs = _linked_configs(tcs_by_id.get(str(it.get("source_tc_id") or ""), {}), req_index)
                    patched += len(apply_requirement_configs(route, it, configs))
                if patched:
                    shared.setdefault("warnings", []).append(
                        f"ExecutableCaseNode-{route}: {patched} 项需求写明的配置未出现在生成结果中，已按需求原值补入（requirement_configs 标为 patched）")
            else:
                # 实网用例靠 expected_result 判定：用例通过标准里的数值门限（2s、95%、-110dBm）改写时丢了就按原文补回
                for it in items:
                    tc = tcs_by_id.get(str(it.get("source_tc_id") or ""), {})
                    lost = uncovered_thresholds(tc.get("pass_fail"), [_text(it.get("expected_result")), _text(it.get("goal"))])
                    if lost:
                        it["expected_result"] = "；".join(x for x in [_text(it.get("expected_result"))] + lost if x)
            return items

        async def run_route(route: str, route_tcs: List[Dict[str, Any]]):
            size = ROUTE_BATCH_SIZE.get(route, 5)
            batches = [route_tcs[i:i + size] for i in range(0, len(route_tcs), size)]
            parts = await asyncio.gather(*(run_batch(route, b) for b in batches))
            return route, [item for part in parts for item in part]

        jobs = [run_route(r, g) for r, g in groups.items() if g]
        results = dict(await asyncio.gather(*jobs)) if jobs else {}

        tc_index = {str(tc.get("tc_id") or ""): tc for tc in tcs}
        bug_ids = [str(b) for b in (shared.get("bug_ids") or []) if str(b).strip()]
        bundles = {r: build_bundle(r, items, tc_index, req_index, bug_ids, source_lines) for r, items in results.items()}
        # 一行配置只要落在任一平台的用例里就不算丢（例如时延门限属于实网用例，不会出现在基站 / 仪表文件里）
        blobs = {r: blob_of({"x": b.get("cases") or b.get("items")}, ["x"]) for r, b in bundles.items()}
        lost = set()
        for r in CONFIG_ROUTES:
            for line in ((bundles.get(r) or {}).get("source_requirement") or {}).get("config_lines") or []:
                if line["status"] != "not_found":
                    continue
                elsewhere = [o for o, blob in blobs.items() if o != r and any(value_present(v, blob) for v in line["values"])]
                if elsewhere:
                    line["status"], line["found_in"] = "other_route", elsewhere
                else:
                    lost.add(line["line_id"])
        if lost:
            shared.setdefault("warnings", []).append(
                f"可执行用例: 需求原文有 {len(lost)} 行配置的取值没有出现在任何平台的用例中（{', '.join(sorted(lost)[:10])}），"
                "请在导出文件的 source_requirement 中确认是否遗漏")
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
        emit(shared, "module_result", {"module": "executable_cases", "data": exec_res["summary"]})
        return "default"

    async def _run_async(self, shared):
        self._shared = shared
        return await super()._run_async(shared)
