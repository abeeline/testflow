"""终稿评审修订：按评审意见修改并重新生成最终测试设计稿（测试设计 + 测试用例）。

只作用于最后的生成物（用例稿生成之后的设计历史记录），不回头改中间阶段：
需求本身要改的意见（取值、范围、验收标准）不在这里改，提示回到“需求澄清与定稿”。

流程（一次任务，两类 LLM 调用，其余全是确定性核对）：
1) 意见落点（final_review_plan.txt）：每条意见判定为 修改 / 新增 / 删除 / 不采纳 / 需改需求 / 无需修改，
   落到具体用例编号，写出给改写人的修改要求；不采纳要给依据。
2) 改写（final_review_revise.txt）：只把受影响的用例送去改写，每条附上对应意见的修改要求；没受影响的用例不动。
3) 闸门（和生成用例时同一套）：
   - 设计合同锁定：tc_id、追溯（req_ids / source_refs）、测试技术、测试环境不随修订改变，改了就恢复并说明；
   - 需求写明的配置原样补回（patch_explicit_configs），数值门限补回（ensure_pass_criteria）；
   - 每条 IE 按 TS 38.331 ASN.1 核对（ie_gate），有错先带着错误让模型改一次，仍不对的用例标待澄清；
   - 结构检查（check_testcase）；
   - 新增字段溯源：修订后多出来的 IE / 配置项 / 参数，如果评审意见、需求、测试点和终稿其他用例里都找不到出处，
     标为“新增字段无出处”，默认不采纳，需要人勾选确认——不允许悄悄编字段；
   - 删除用例不能让任何需求失去覆盖。
4) 每条修改给出改前 / 改后字段级差异和对应的意见编号；人逐条采纳后才写回记录，生成新版本（v2、v3…），
   改前的整份终稿另存快照，可以撤销回上一版。
"""
import asyncio
import copy
import difflib
import hashlib
import json
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from core import ie_gate
from core.grouping import attach_suites
from core.llm import generate_json
from core.quality import check_testcase, ensure_pass_criteria, finalize_pending, req_index
from core.tcd import TCD_SCHEMA, normalize_tcd, patch_explicit_configs
from utils.req_configs import normalize_explicit_configs

DECISIONS = {
    "revise": "修改用例",
    "add": "新增用例",
    "remove": "删除用例",
    "reject": "不采纳",
    "requirement_change": "需改需求",
    "no_change": "无需修改",
}
ACTIONABLE = {"revise", "add", "remove"}
REVISE_BATCH = 3

PLAN_SCHEMA = {
    "type": "object",
    "required": ["comments"],
    "properties": {"comments": {"type": "array", "items": {
        "type": "object", "required": ["comment_id", "decision"],
        "properties": {
            "comment_id": {"type": "string"},
            "understanding": {"type": "string"},
            "decision": {"type": "string"},
            "targets": {"type": "array"},
            "instruction": {"type": "string"},
            "reason": {"type": "string"},
            "add": {"type": "array"},
        }}}},
}

REVISE_SCHEMA = {
    "type": "object",
    "required": ["testcases"],
    "properties": {
        "testcases": {"type": "array", "items": TCD_SCHEMA},
        "change_notes": {"type": "array"},
    },
}


# ---------- 评审意见 ----------

_TARGET = r"(?:TC|ROW|REQ|AR|SR)-[\w.-]+"
_LINE = re.compile(rf"^\s*(?:\d+\s*[.、)）]\s*)?(?:\[(?P<t1>[^\]]+)\]|【(?P<t3>[^】]+)】|(?P<t2>{_TARGET})\s*[:：])\s*(?P<text>.+)$")


def parse_comments(raw: Any) -> List[Dict[str, str]]:
    """评审意见：可以是 [{text, target}]，也可以是多行文本（每行一条，行首写 [TC-003] 或 TC-003： 指定用例）。"""
    items: List[Dict[str, str]] = []
    if isinstance(raw, str):
        raw = [ln for ln in raw.splitlines() if ln.strip()]
    for entry in raw or []:
        if isinstance(entry, dict):
            text = str(entry.get("text") or "").strip()
            target = str(entry.get("target") or "").strip()
        else:
            text, target = str(entry or "").strip(), ""
        if not text:
            continue
        m = _LINE.match(text)
        if m and not target:
            target = (m.group("t1") or m.group("t2") or m.group("t3") or "").strip()
            text = m.group("text").strip()
        items.append({"text": text, "target": target})
    for n, it in enumerate(items, start=1):
        it["comment_id"] = f"RC-{n:02d}"
    return items


# ---------- 指纹 ----------

def fingerprint(test_design_spec: Any, test_case_spec: Any) -> str:
    text = json.dumps({"d": test_design_spec or {}, "c": test_case_spec or {}}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


# ---------- 给模型的视图 ----------

def _tc_brief(tc: Dict[str, Any]) -> Dict[str, Any]:
    tp = tc.get("test_purpose") or {}
    return {
        "tc_id": tc.get("tc_id"), "title": tc.get("title"), "technique": tc.get("technique"),
        "req_ids": (tc.get("trace") or {}).get("req_ids") or [], "row_ids": (tc.get("trace") or {}).get("source_refs") or [],
        "env": (tc.get("test_environment") or {}).get("primary") if isinstance(tc.get("test_environment"), dict) else tc.get("test_environment"),
        "purpose": {k: tp.get(k) for k in ("with", "when", "then") if tp.get(k)},
        "messages": [m.get("message") for m in tc.get("message_contents") or [] if m.get("message")],
        "steps": len(tc.get("procedure") or []),
        "pass_fail": tc.get("pass_fail") or [],
        **({"status": tc["status"]} if tc.get("status") else {}),
    }


def _req_brief(req: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: req.get(k) for k in ("req_id", "title", "priority", "expected") if req.get(k)}
    acc = (req.get("acceptance") or {}).get("pass_fail")
    if acc:
        out["acceptance"] = acc
    cfgs = normalize_explicit_configs(req)
    if cfgs:
        out["explicit_configs"] = [{k: c.get(k) for k in ("name", "value", "target") if c.get(k) not in (None, "")} for c in cfgs]
    return out


def _row_brief(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: row.get(k) for k in ("row_id", "req_id", "objective_id", "technique", "scenario", "test_purpose",
                                    "key_configuration", "pass_criteria", "references", "test_environment") if row.get(k)}


# ---------- 意见落点 ----------

def _as_ids(value: Any) -> List[str]:
    if isinstance(value, str):
        value = re.split(r"[,，、\s]+", value)
    return [str(x).strip() for x in value or [] if str(x).strip()]


def validate_plan(raw: Any, comments: List[Dict[str, str]], tcs: List[Dict[str, Any]],
                  rows: List[Dict[str, Any]], reqs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把模型给的意见落点规整成可执行的计划。落不到实处的（编号不存在、挂到不存在的需求）改成不可执行并写明原因。"""
    tc_ids = [str(tc.get("tc_id")) for tc in tcs]
    by_row: Dict[str, List[str]] = {}
    for tc in tcs:
        for r in (tc.get("trace") or {}).get("source_refs") or []:
            by_row.setdefault(str(r), []).append(str(tc.get("tc_id")))
    by_req: Dict[str, List[str]] = {}
    for tc in tcs:
        for r in (tc.get("trace") or {}).get("req_ids") or []:
            by_req.setdefault(str(r), []).append(str(tc.get("tc_id")))

    def resolve(ids: Iterable[str]) -> List[str]:
        out: List[str] = []
        for i in ids:
            for x in ([i] if i in tc_ids else by_row.get(i) or []):
                if x not in out:
                    out.append(x)
        return out

    got = {}
    for it in (raw or {}).get("comments") or []:
        if isinstance(it, dict) and str(it.get("comment_id") or "") not in got:
            got[str(it.get("comment_id"))] = it
    plan = []
    for c in comments:
        it = got.get(c["comment_id"]) or {}
        decision = str(it.get("decision") or "").strip().lower()
        if decision not in DECISIONS:
            decision = "revise" if c.get("target") else "no_change"
        item = {
            "comment_id": c["comment_id"], "text": c["text"], "target": c.get("target", ""),
            "understanding": str(it.get("understanding") or "").strip(),
            "decision": decision,
            "instruction": str(it.get("instruction") or "").strip() or c["text"],
            "reason": str(it.get("reason") or "").strip(),
            "targets": [], "add": [],
        }
        if not it:
            item["reason"] = item["reason"] or "模型没有给出这条意见的处理，按意见原文处理"
        if decision in ("revise", "remove"):
            targets = resolve(_as_ids(it.get("targets")))
            if not targets and c.get("target"):
                targets = resolve([c["target"]]) or list(by_req.get(c["target"], []))
            if not targets:
                item["decision"] = "no_change"
                item["reason"] = "没能确定这条意见对应哪条用例，请在意见前写上用例编号（如 [TC-003]）后重试"
            item["targets"] = targets
        if decision == "add":
            adds = []
            for a in it.get("add") or []:
                if not isinstance(a, dict):
                    continue
                rid = str(a.get("req_id") or c.get("target") or "").strip()
                if rid not in reqs:
                    continue
                adds.append({"req_id": rid, "scenario": str(a.get("scenario") or "").strip() or c["text"][:60],
                             "technique": str(a.get("technique") or "normal"),
                             "test_purpose": a.get("test_purpose") if isinstance(a.get("test_purpose"), dict) else {},
                             "pass_criteria": _as_list_text(a.get("pass_criteria")),
                             "references": _as_list_text(a.get("references")),
                             "base_row": str(a.get("base_row") or "").strip()})
            if not adds:
                item["decision"] = "requirement_change"
                item["reason"] = item["reason"] or "新增用例必须挂到已定稿的需求上；这条意见找不到对应需求，需要先在需求澄清里补需求"
            item["add"] = adds
        plan.append(item)
    return plan


def _as_list_text(v: Any) -> List[str]:
    if v in (None, ""):
        return []
    return [str(x).strip() for x in (v if isinstance(v, list) else [v]) if str(x).strip()]


# ---------- 新增字段溯源 ----------

def _leaf(name: str) -> str:
    leaf = re.split(r"[./]", re.sub(r"\[\d+\]", "", str(name)))[-1]
    return leaf.strip()


def _base_name(name: str) -> str:
    return re.sub(r"-[rv]\d+$", "", _leaf(name)).lower()


def field_keys(tc: Dict[str, Any]) -> Dict[str, str]:
    """用例里出现的“字段”：IE、配置项、步骤参数、扫描参数。返回 {键: 字段名}。"""
    out: Dict[str, str] = {}
    for m in tc.get("message_contents") or []:
        for ie in m.get("ies") or []:
            if ie.get("path"):
                out[f"IE {m.get('message', '')}.{ie['path']}"] = str(ie["path"])
    cfg = tc.get("configuration") or {}
    for i, cell in enumerate(cfg.get("cells") or []):
        for k in cell if isinstance(cell, dict) else {}:
            if k != "cell_id":
                out[f"配置 小区.{k}"] = str(k)
    for part, label in (("core", "核心网"), ("ue", "UE"), ("other", "其他")):
        for k in (cfg.get(part) or {}) if isinstance(cfg.get(part), dict) else {}:
            out[f"配置 {label}.{k}"] = str(k)
    for p in tc.get("procedure") or []:
        for k in (p.get("params") or {}) if isinstance(p.get("params"), dict) else {}:
            out[f"步骤参数 {k}"] = str(k)
    for v in tc.get("parameter_variations") or []:
        if isinstance(v, dict) and v.get("name"):
            out[f"扫描参数 {v['name']}"] = str(v["name"])
    return out


def unbacked_fields(before: Optional[Dict[str, Any]], after: Dict[str, Any], evidence: str,
                    known: Iterable[str]) -> List[str]:
    """修订后新出现、又找不到出处的字段。出处：评审意见 / 需求 / 测试点原文里提到了，或者终稿其他用例里已经在用，或改前就有同名字段。"""
    old = field_keys(before or {})
    old_names = {_base_name(v) for v in old.values()}
    known_keys = set(known)
    ev = evidence.lower()
    out = []
    for key, name in field_keys(after).items():
        if key in old or key in known_keys or "（需求值）" in name:
            continue
        base = _base_name(name)
        if not base or base in old_names:
            continue
        if base in ev or _leaf(name).lower() in ev:
            continue
        out.append(key)
    return out


# ---------- 差异 ----------

def _txt(v: Any) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return "" if v is None else str(v)


def _step_line(p: Dict[str, Any]) -> str:
    parts = [str(p.get("actor") or "")]
    if p.get("direction"):
        parts.append(str(p["direction"]))
    if p.get("layer"):
        parts.append(str(p["layer"]))
    parts.append(str(p.get("message") or p.get("action") or ""))
    if p.get("msg_ref"):
        parts.append(f"({p['msg_ref']})")
    if p.get("params"):
        parts.append(_txt(p["params"]))
    line = " ".join(x for x in parts if x)
    if p.get("expected"):
        line += f" → {p['expected']}"
    if p.get("verdict"):
        line += " ✔"
    return line


def _keyed(tc: Dict[str, Any]) -> Dict[str, str]:
    tp = tc.get("test_purpose") or {}
    out = {"标题": _txt(tc.get("title")), "优先级": _txt(tc.get("priority")),
           "测试目的 with": _txt(tp.get("with")), "测试目的 when": _txt(tp.get("when")), "测试目的 then": _txt(tp.get("then")),
           "适用性": _txt(tc.get("applicability")), "状态": _txt(tc.get("status"))}
    cfg = tc.get("configuration") or {}
    for i, cell in enumerate(cfg.get("cells") or []):
        cid = (cell or {}).get("cell_id") or f"Cell{i + 1}"
        for k, v in (cell or {}).items():
            if k != "cell_id":
                out[f"配置 小区 {cid}.{k}"] = _txt(v)
    for part, label in (("core", "核心网"), ("ue", "UE"), ("other", "其他")):
        for k, v in ((cfg.get(part) or {}) if isinstance(cfg.get(part), dict) else {}).items():
            out[f"配置 {label}.{k}"] = _txt(v)
    for m in tc.get("message_contents") or []:
        head = f"消息 {m.get('msg_id', '')} {m.get('message', '')}".strip()
        for ie in m.get("ies") or []:
            out[f"{head} · {ie.get('path')}"] = _txt(ie.get("value"))
    for v in tc.get("parameter_variations") or []:
        if isinstance(v, dict) and v.get("name"):
            out[f"参数扫描 {v['name']}"] = _txt(v.get("values"))
    return {k: v for k, v in out.items() if v != ""}


def _lists(tc: Dict[str, Any]) -> Dict[str, List[str]]:
    ic = tc.get("initial_conditions") or {}
    return {
        "参考条款": [str(x) for x in tc.get("references") or []],
        "初始条件 网络侧": [str(x) for x in ic.get("system_simulator") or []],
        "初始条件 UE": [str(x) for x in ic.get("ue") or []],
        "Preamble": [str(x) for x in ic.get("preamble") or []],
        "测试步骤": [_step_line(p) for p in tc.get("procedure") or [] if isinstance(p, dict)],
        "通过标准": [str(x) for x in tc.get("pass_fail") or [] if x != "待补充通过条件"],
        "后置": [str(x) for x in tc.get("postamble") or []],
        "待确认": [str(x) for x in tc.get("open_points") or []],
    }


def field_diff(before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """字段级差异：[{field, kind: added|removed|changed, before, after}]。列表类字段按行比对，插一步不会让后面每步都算“改了”。"""
    before, after = before or {}, after or {}
    out: List[Dict[str, str]] = []
    kb, ka = _keyed(before), _keyed(after)
    for k in list(dict.fromkeys(list(kb) + list(ka))):
        b, a = kb.get(k), ka.get(k)
        if b == a:
            continue
        kind = "added" if b is None else "removed" if a is None else "changed"
        out.append({"field": k, "kind": kind, "before": b or "", "after": a or ""})
    lb, la = _lists(before), _lists(after)
    for k in lb:
        b, a = lb[k], la[k]
        if b == a:
            continue
        sm = difflib.SequenceMatcher(a=b, b=a, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            olds, news = b[i1:i2], a[j1:j2]
            for n in range(max(len(olds), len(news))):
                o = olds[n] if n < len(olds) else None
                w = news[n] if n < len(news) else None
                kind = "added" if o is None else "removed" if w is None else "changed"
                pos = (j1 + n + 1) if w is not None else (i1 + n + 1)
                out.append({"field": f"{k} #{pos}", "kind": kind, "before": o or "", "after": w or ""})
    return out


# ---------- 闸门 ----------

def _evidence(comment_texts: List[str], reqs: List[Dict[str, Any]], row: Optional[Dict[str, Any]]) -> str:
    parts = list(comment_texts)
    for r in reqs:
        parts.append(json.dumps({k: r.get(k) for k in ("title", "description", "source_text", "trigger", "expected",
                                                       "acceptance", "explicit_configs", "clarification")},
                                ensure_ascii=False, default=str))
    if row:
        parts.append(json.dumps(row, ensure_ascii=False, default=str))
    return "\n".join(parts)


def gate_revised(raw: Dict[str, Any], *, before: Optional[Dict[str, Any]], row: Optional[Dict[str, Any]],
                 reqs: Dict[str, Dict[str, Any]], spec: Dict[str, Any], comment_texts: List[str],
                 known_fields: Iterable[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """修订后的用例过闸门，返回 (用例, 报告)。报告：locked / ie_errors / ie_fixed / issues / unbacked / conflicts / status。"""
    tc = normalize_tcd(raw)
    locked: List[str] = []
    if before:
        if tc["tc_id"] != before.get("tc_id"):
            tc["tc_id"] = before.get("tc_id")
        b_trace = before.get("trace") or {}
        if tc["trace"].get("req_ids") != b_trace.get("req_ids") or tc["trace"].get("source_refs") != b_trace.get("source_refs"):
            locked.append("追溯关系（需求 / 测试点）沿用终稿，修订不能改变")
            tc["trace"] = copy.deepcopy(b_trace)
        b_env = (before.get("test_environment") or {}) if isinstance(before.get("test_environment"), dict) else {}
        a_env = (tc.get("test_environment") or {}) if isinstance(tc.get("test_environment"), dict) else {}
        if b_env and a_env.get("primary") != b_env.get("primary"):
            locked.append(f"测试环境沿用测试设计（{b_env.get('primary')}），要换环境请在测试设计里改")
        if before.get("test_environment") is not None:
            tc["test_environment"] = copy.deepcopy(before.get("test_environment"))
        if before.get("technique") and tc["technique"] != before.get("technique"):
            locked.append(f"测试技术沿用测试设计（{before.get('technique')}）")
            tc["technique"] = before.get("technique")
        for k in ("objective_id", "suite"):
            if before.get(k) and not tc.get(k):
                tc[k] = copy.deepcopy(before[k])
    elif row:
        tc["trace"] = {"req_ids": [str(row.get("req_id"))], "source_refs": [str(row.get("row_id"))]}
        tc["technique"] = row.get("technique") or tc["technique"]
        tc["objective_id"] = row.get("objective_id") or tc.get("objective_id", "")
        if row.get("test_environment"):
            tc["test_environment"] = copy.deepcopy(row["test_environment"])
    # 原来的待澄清标记让闸门重新判断
    tc.pop("status", None)
    tc.pop("blocked_by", None)
    tc["open_points"] = [x for x in tc.get("open_points") or [] if not str(x).startswith("待澄清：")]

    configs = []
    for rid in tc["trace"].get("req_ids") or []:
        if str(rid) in reqs:
            configs.extend(normalize_explicit_configs(reqs[str(rid)]))
    cfg_res = patch_explicit_configs(tc, configs)
    conflicts = [f"{r['name']}={r['value']}：{r.get('note', '')}" for r in cfg_res if r.get("status") == "conflict"]
    patched = [f"{r['name']}={r['value']}" for r in cfg_res if r.get("status") == "patched"]
    if row:
        ensure_pass_criteria(tc, row)
    ie_rep = ie_gate.check_messages(tc.get("message_contents") or [], autofix=True)
    issues = check_testcase(tc)
    req_objs = [reqs[str(r)] for r in tc["trace"].get("req_ids") or [] if str(r) in reqs]
    unbacked = unbacked_fields(before, tc, _evidence(comment_texts, req_objs, row), known_fields)
    finalize_pending([tc], spec)
    if ie_rep["errors"]:
        status = "blocked"
    elif unbacked or conflicts or issues:
        status = "warn"
    else:
        status = "ok"
    return tc, {"locked": locked, "ie_errors": ie_rep["errors"], "ie_fixed": ie_rep["fixed"], "issues": issues,
                "unbacked": unbacked, "conflicts": conflicts, "patched": patched, "status": status}


# ---------- 编排 ----------

def _emit(events: Any, node: str, label: str, detail: str = "") -> None:
    if events is not None:
        events.emit("node_running", {"node": node, "label": label, "detail": detail})


def _next_id(existing: Iterable[str], prefix: str) -> Callable[[], str]:
    nums = [int(m.group(1)) for x in existing for m in [re.match(rf"{prefix}-(\d+)$", str(x))] if m]
    counter = {"n": max(nums or [0])}

    def nxt() -> str:
        counter["n"] += 1
        return f"{prefix}-{counter['n']:03d}"
    return nxt


async def build_proposal(shared: Dict[str, Any], record: Dict[str, Any], comments: List[Dict[str, str]],
                         requirement_view: Callable[[Dict[str, Any]], Dict[str, Any]], events: Any = None) -> Dict[str, Any]:
    """生成修订提案（不写回记录）。shared 需要 llm_client，用来记用量和告警。"""
    design = record.get("test_design_spec") or {}
    cases = record.get("test_case_spec") or {}
    tcs: List[Dict[str, Any]] = [tc for tc in cases.get("testcases") or [] if isinstance(tc, dict)]
    rows: List[Dict[str, Any]] = [r for r in design.get("integrated_matrix") or [] if isinstance(r, dict)]
    spec = record.get("requirement_spec") or {}
    reqs = req_index(spec.get("final_requirements") or [])
    row_map = {str(r.get("row_id")): r for r in rows}
    tc_map = {str(tc.get("tc_id")): tc for tc in tcs}
    context = {
        "product_profile": (record.get("product_profile") or {}).get("selected", record.get("product_profile") or {}),
        "assumptions": spec.get("assumptions", []),
    }

    _emit(events, "FinalReviewPlan", "理解评审意见", f"{len(comments)} 条")
    raw_plan = await asyncio.to_thread(
        generate_json, shared=shared, template_name="final_review_plan.txt",
        variables={
            "comments_json": json.dumps(comments, ensure_ascii=False),
            "testcases_json": json.dumps([_tc_brief(tc) for tc in tcs], ensure_ascii=False),
            "rows_json": json.dumps([{k: r.get(k) for k in ("row_id", "req_id", "technique", "scenario")} for r in rows], ensure_ascii=False),
            "requirements_json": json.dumps([_req_brief(r) for r in reqs.values()], ensure_ascii=False),
            "context_json": json.dumps(context, ensure_ascii=False),
        },
        schema=PLAN_SCHEMA, warn_tag="FinalReviewPlan", max_retries=1)
    plan = validate_plan(raw_plan, comments, tcs, rows, reqs)

    # 汇总每条用例要落实的意见
    work: Dict[str, List[Dict[str, Any]]] = {}
    removes: Dict[str, List[str]] = {}
    adds: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for p in plan:
        if p["decision"] == "revise":
            for t in p["targets"]:
                work.setdefault(t, []).append(p)
        elif p["decision"] == "remove":
            for t in p["targets"]:
                removes.setdefault(t, []).append(p["comment_id"])
        elif p["decision"] == "add":
            for a in p["add"]:
                adds.append((p, a))
    for t in removes:  # 同一条用例既要删又要改：以删为准，改的意见记在删除那条修改上
        work.pop(t, None)

    new_row_id = _next_id(row_map, "ROW")
    new_tc_id = _next_id(tc_map, "TC")
    new_items: List[Dict[str, Any]] = []  # {row, tc_id, plan}
    for p, a in adds:
        base = row_map.get(a.get("base_row")) or next((r for r in rows if str(r.get("req_id")) == a["req_id"]), {})
        tp = a.get("test_purpose") or {}
        row = {
            "row_id": new_row_id(), "req_id": a["req_id"], "objective_id": base.get("objective_id", ""),
            "technique": a.get("technique") or "normal", "scenario": a["scenario"],
            "test_purpose": {"with": str(tp.get("with") or ""), "when": str(tp.get("when") or a["scenario"]), "then": str(tp.get("then") or "")},
            "key_configuration": copy.deepcopy(base.get("key_configuration") or {}),
            "pass_criteria": a.get("pass_criteria") or ["关键指标满足需求标准"],
            "references": a.get("references") or list(base.get("references") or []),
            "test_environment": copy.deepcopy(base.get("test_environment") or {}),
            "added_by_review": p["comment_id"],
        }
        new_items.append({"row": row, "tc_id": new_tc_id(), "plan": p})

    # 改写
    jobs: List[Dict[str, Any]] = []
    for tc_id, ps in work.items():
        tc = tc_map[tc_id]
        row = next((row_map[r] for r in (tc.get("trace") or {}).get("source_refs") or [] if r in row_map), None)
        jobs.append({"kind": "update", "tc_id": tc_id, "before": tc, "row": row, "plans": ps})
    for it in new_items:
        jobs.append({"kind": "add", "tc_id": it["tc_id"], "before": None, "row": it["row"], "plans": [it["plan"]]})

    known_by_req: Dict[str, set] = {}
    for tc in tcs:
        keys = set(field_keys(tc))
        for r in (tc.get("trace") or {}).get("req_ids") or []:
            known_by_req.setdefault(str(r), set()).update(keys)

    async def revise(batch: List[Dict[str, Any]], feedback: str = "") -> Dict[str, Any]:
        items = []
        for j in batch:
            entry = {"tc_id": j["tc_id"], "new": j["kind"] == "add",
                     "comments": [{"comment_id": p["comment_id"], "text": p["text"], "instruction": p["instruction"]} for p in j["plans"]],
                     "matrix_row": _row_brief(j["row"]) if j["row"] else None}
            if j["before"] is not None:
                entry["current"] = {k: v for k, v in j["before"].items() if k not in ("steps", "preconditions", "expected", "suite")}
            items.append(entry)
        rids = list(dict.fromkeys(str(r) for j in batch for r in (
            ((j["before"] or {}).get("trace") or {}).get("req_ids") or [j["row"].get("req_id") if j["row"] else ""]) if r))
        data = await asyncio.to_thread(
            generate_json, shared=shared, template_name="final_review_revise.txt",
            variables={
                "items_json": json.dumps(items, ensure_ascii=False, default=str),
                "requirements_json": json.dumps([requirement_view(reqs[r]) for r in rids if r in reqs], ensure_ascii=False, default=str),
                "context_json": json.dumps({**context, "feedback": feedback}, ensure_ascii=False),
            },
            schema=REVISE_SCHEMA, warn_tag="FinalReviewRevise", max_retries=1)
        return data

    def pick(data: Dict[str, Any], j: Dict[str, Any], pos: int, n: int) -> Optional[Dict[str, Any]]:
        got = [tc for tc in data.get("testcases") or [] if isinstance(tc, dict)]
        hit = next((tc for tc in got if str(tc.get("tc_id")) == j["tc_id"]), None)
        if hit is None and len(got) == n:
            hit = got[pos]
        return hit

    def notes_for(data: Dict[str, Any], tc_id: str) -> List[Dict[str, Any]]:
        return [x for x in data.get("change_notes") or [] if isinstance(x, dict) and str(x.get("tc_id")) == tc_id]

    changes: List[Dict[str, Any]] = []
    batches = [jobs[i:i + REVISE_BATCH] for i in range(0, len(jobs), REVISE_BATCH)]
    if jobs:
        _emit(events, "FinalReviewRevise", "按意见改写用例", f"{len(work)} 条修改、{len(new_items)} 条新增")

    async def run_batch(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        try:
            data = await revise(batch)
        except Exception as exc:  # 这一批失败：逐条标失败，不影响其他批
            return [{"job": j, "error": str(exc)} for j in batch]
        retry: List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]] = []
        for pos, j in enumerate(batch):
            raw = pick(data, j, pos, len(batch))
            if raw is None:
                out.append({"job": j, "error": "模型没有返回这条用例"})
                continue
            if j["kind"] == "add":
                raw = {**raw, "tc_id": j["tc_id"]}
            known = set()
            for r in ((j["before"] or {}).get("trace") or {}).get("req_ids") or [j["row"].get("req_id") if j["row"] else ""]:
                known |= known_by_req.get(str(r), set())
            texts = [p["text"] for p in j["plans"]]
            tc, rep = gate_revised(copy.deepcopy(raw), before=j["before"], row=j["row"], reqs=reqs, spec=spec,
                                   comment_texts=texts, known_fields=known)
            res = {"job": j, "tc": tc, "report": rep, "notes": notes_for(data, j["tc_id"]), "raw": raw, "known": known, "texts": texts}
            if rep["ie_errors"] or rep["issues"]:
                retry.append((j, res, raw, rep))
            out.append(res)
        # IE 错误 / 结构问题：带着具体错误让模型在改写结果上再改一次
        for j, res, raw, rep in retry:
            fb = "上一次修订结果没有通过核对，请逐条改正（只改这些问题，评审意见的修改保留）：\n" + "\n".join(
                [f"- {e}" for e in rep["ie_errors"]] + [f"- {e}" for e in rep["issues"]])
            j2 = {**j, "before": j["before"]}
            try:
                data2 = await revise([{**j2, "plans": j["plans"]}], feedback=fb + "\n上一次的结果：" + json.dumps(raw, ensure_ascii=False, default=str)[:6000])
                raw2 = pick(data2, j, 0, 1)
            except Exception:
                raw2 = None
            if raw2 is None:
                continue
            if j["kind"] == "add":
                raw2 = {**raw2, "tc_id": j["tc_id"]}
            tc2, rep2 = gate_revised(copy.deepcopy(raw2), before=j["before"], row=j["row"], reqs=reqs, spec=spec,
                                     comment_texts=res["texts"], known_fields=res["known"])
            if len(rep2["ie_errors"]) + len(rep2["issues"]) < len(rep["ie_errors"]) + len(rep["issues"]):
                res.update({"tc": tc2, "report": {**rep2, "repaired": True}, "notes": notes_for(data2, j["tc_id"]) or res["notes"]})
        return out

    results: List[Dict[str, Any]] = []
    for part in await asyncio.gather(*(run_batch(b) for b in batches)):
        results.extend(part)

    _emit(events, "FinalReviewGate", "核对修订结果", "IE 闸门 · 需求配置 · 追溯 · 新增字段")
    n = 0
    for res in results:
        j = res["job"]
        n += 1
        cids = [p["comment_id"] for p in j["plans"]]
        base = {"change_id": f"CH-{n:02d}", "op": j["kind"], "tc_id": j["tc_id"], "comment_ids": cids,
                "title": (res.get("tc") or j["before"] or {}).get("title") or (j["row"] or {}).get("scenario", "")}
        if res.get("error"):
            changes.append({**base, "status": "failed", "error": res["error"], "diff": [], "gate": {}})
            continue
        diff = field_diff(j["before"], res["tc"])
        if j["kind"] == "update" and not diff:
            changes.append({**base, "status": "noop", "diff": [], "gate": res["report"], "notes": res["notes"]})
            continue
        ch = {**base, "status": res["report"]["status"], "diff": diff, "gate": res["report"], "notes": res["notes"],
              "after": res["tc"]}
        if j["kind"] == "add":
            ch["row"] = j["row"]
        changes.append(ch)

    # 删除：不能让需求失去覆盖
    remaining = [tc for tc in tcs if str(tc.get("tc_id")) not in removes]
    covered_after = {str(r) for tc in remaining for r in (tc.get("trace") or {}).get("req_ids") or []}
    covered_after |= {str(it["row"]["req_id"]) for it in new_items}
    for tc_id, cids in removes.items():
        n += 1
        tc = tc_map[tc_id]
        lost = [str(r) for r in (tc.get("trace") or {}).get("req_ids") or [] if str(r) in reqs and str(r) not in covered_after]
        gate = {"lost_coverage": lost}
        changes.append({"change_id": f"CH-{n:02d}", "op": "remove", "tc_id": tc_id, "comment_ids": cids,
                        "title": tc.get("title", ""), "status": "blocked" if lost else "ok", "gate": gate,
                        "diff": [{"field": "整条用例", "kind": "removed", "before": f"{tc_id} {tc.get('title', '')}", "after": ""}]})

    by_comment: Dict[str, List[str]] = {}
    for ch in changes:
        if ch["status"] not in ("noop", "failed"):
            for c in ch["comment_ids"]:
                by_comment.setdefault(c, []).append(ch["change_id"])
    for p in plan:
        p["change_ids"] = by_comment.get(p["comment_id"], [])
        if p["decision"] in ACTIONABLE and not p["change_ids"]:
            fails = [ch for ch in changes if p["comment_id"] in ch["comment_ids"]]
            p["outcome"] = "改写失败" if any(c["status"] == "failed" for c in fails) else "改写后没有实际变化"
        else:
            p["outcome"] = ""
    return {
        "proposal_id": time.strftime("%Y%m%d%H%M%S"),
        "record_id": record.get("record_id", ""),
        "base_fingerprint": fingerprint(design, cases),
        "comments": plan,
        "changes": changes,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    }


# ---------- 采纳 ----------

class RevisionError(ValueError):
    pass


def apply_changes(record: Dict[str, Any], proposal: Dict[str, Any], accepted: Iterable[str]) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """把采纳的修改写进终稿副本，返回 (test_design_spec, test_case_spec, applied)。不改 record 本身。"""
    design = copy.deepcopy(record.get("test_design_spec") or {})
    cases = copy.deepcopy(record.get("test_case_spec") or {})
    if fingerprint(record.get("test_design_spec") or {}, record.get("test_case_spec") or {}) != proposal.get("base_fingerprint"):
        raise RevisionError("终稿在生成修订之后又被改过（重新生成或采纳了别的修订），这份修订提案已过期，请重新生成修订")
    accepted = set(accepted)
    tcs: List[Dict[str, Any]] = [tc for tc in cases.get("testcases") or [] if isinstance(tc, dict)]
    rows: List[Dict[str, Any]] = [r for r in design.get("integrated_matrix") or [] if isinstance(r, dict)]
    reqs = req_index(((record.get("requirement_spec") or {}).get("final_requirements")) or [])
    applied = []
    for ch in proposal.get("changes") or []:
        if ch.get("change_id") not in accepted:
            continue
        if ch.get("status") in ("failed", "noop"):
            continue
        op = ch.get("op")
        if op == "update":
            idx = next((i for i, tc in enumerate(tcs) if tc.get("tc_id") == ch["tc_id"]), None)
            if idx is None or not isinstance(ch.get("after"), dict):
                continue
            tcs[idx] = copy.deepcopy(ch["after"])
        elif op == "add":
            if not isinstance(ch.get("after"), dict) or not isinstance(ch.get("row"), dict):
                continue
            row = copy.deepcopy(ch["row"])
            if any(r.get("row_id") == row["row_id"] for r in rows):
                row["row_id"] = _next_id([r.get("row_id") for r in rows], "ROW")()
            tc = copy.deepcopy(ch["after"])
            if any(t.get("tc_id") == tc.get("tc_id") for t in tcs):
                tc["tc_id"] = _next_id([t.get("tc_id") for t in tcs], "TC")()
            tc.setdefault("trace", {})["source_refs"] = [row["row_id"]]
            rows.append(row)
            tcs.append(tc)
        elif op == "remove":
            tcs = [tc for tc in tcs if tc.get("tc_id") != ch["tc_id"]]
        else:
            continue
        applied.append(ch)
    # 删除后没有用例的测试点一并去掉；任何需求失去覆盖都不允许
    old_tcs = (record.get("test_case_spec") or {}).get("testcases") or []
    used_before = {str(r) for tc in old_tcs for r in (tc.get("trace") or {}).get("source_refs") or []}
    used_now = {str(r) for tc in tcs for r in (tc.get("trace") or {}).get("source_refs") or []}
    rows = [r for r in rows if str(r.get("row_id")) in used_now or str(r.get("row_id")) not in used_before]
    before_cov = {str(r) for tc in (record.get("test_case_spec") or {}).get("testcases") or [] for r in (tc.get("trace") or {}).get("req_ids") or []}
    after_cov = {str(r) for tc in tcs for r in (tc.get("trace") or {}).get("req_ids") or []}
    lost = sorted(r for r in before_cov - after_cov if r in reqs)
    if lost:
        raise RevisionError(f"采纳后需求 {', '.join(lost)} 将没有任何用例覆盖，请不要采纳对应的删除")
    attach_suites([tc for tc in tcs if not tc.get("suite")], reqs)
    design["integrated_matrix"] = rows
    cases["testcases"] = tcs
    return design, cases, applied


def revision_entry(version: int, proposal: Dict[str, Any], applied: List[Dict[str, Any]], reviewer: str,
                   note: str, result_fp: str) -> Dict[str, Any]:
    """写进记录的修订日志（不含整条用例，体积小；改前整份终稿另存快照）。"""
    applied_ids = {c["change_id"] for c in applied}
    return {
        "version": version,
        "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "reviewer": reviewer,
        "note": note,
        "base_fingerprint": proposal.get("base_fingerprint"),
        "result_fingerprint": result_fp,
        "comments": [{k: c.get(k) for k in ("comment_id", "text", "target", "understanding", "decision", "reason", "change_ids")}
                     | {"applied": [x for x in c.get("change_ids") or [] if x in applied_ids]}
                     for c in proposal.get("comments") or []],
        "changes": [{"change_id": c["change_id"], "op": c["op"], "tc_id": (c.get("after") or {}).get("tc_id") or c["tc_id"],
                     "title": c.get("title", ""), "comment_ids": c.get("comment_ids", []), "status": c.get("status"),
                     "fields": len(c.get("diff") or []),
                     "diff": (c.get("diff") or [])[:40],
                     "unbacked": (c.get("gate") or {}).get("unbacked", []),
                     "ie_errors": (c.get("gate") or {}).get("ie_errors", [])}
                    for c in applied],
        "skipped": [c["change_id"] for c in proposal.get("changes") or [] if c["change_id"] not in applied_ids
                    and c.get("status") not in ("noop", "failed")],
    }
