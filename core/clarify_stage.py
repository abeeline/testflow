"""需求澄清与定稿：需求评审之后、测试设计之前的一步。

    评审出的澄清单（core/clarification.py）
      → 需求方逐条回答 / 采纳建议 / 豁免（页面填写或 Excel 回填，按 CLR 编号对回）
      → 回答本身再按规范核对一遍（字段是否存在、写的位置对不对、取值能不能编码），不对的退回
      → 能一一对应的改动写回需求（字段改名、删掉不存在的字段、取值改成规范编码），留下改前改后
      → 逐条确认“AI 对需求的理解”（复述卡片）
      → 定稿：生成基线版本（版本号、确认人、时间、指纹）。测试设计只接受定稿的需求，
        或者用户明确选择“带待澄清继续”
定稿后需求又变了（指纹对不上）就是“基线已过期”，要重新定稿；已经生成的设计/用例按影响分析标出要重做的部分。
"""
import datetime as dt
import hashlib
import io
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core import asn1_paths as A
from core import req_checks
from core.clarification import _IE_TOKEN, _MSG_WORDS, _NOT_IE, _field_status, summary_text

STATUS_LABELS = {"open": "待回答", "resolved_by_spec": "规范已定", "resolved_by_owner": "需求方已答", "waived": "已豁免"}
KIND_LABELS = {"unknown_field": "字段不存在", "renamed": "字段名版本后缀", "enum_as_field": "枚举值当字段", "wrong_location": "位置写错",
               "wrong_message": "消息写错", "value_type": "取值不合规", "spec_doubt": "评审疑问", "release_mismatch": "版本不一致",
               "text_config_conflict": "正文与配置矛盾", "inconsistent_value": "同组取值不同", "duplicate": "疑似重复",
               "ambiguity": "歧义"}
ACTIONS = {"answer": "回答", "accept": "采纳建议", "waive": "豁免", "reopen": "重开"}
_ACTION_BY_LABEL = {v: k for k, v in ACTIONS.items()}
_REMOVE = re.compile(r"删除|删去|去掉|移除|不存在|不测|不校验|取消")
_RENAME = re.compile(r"(?:改为|改成|应为|更正为|替换为|换成|即为|实际是|应使用|用)\s*[：:]?\s*([a-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)")
_CLAUSE = re.compile(r"[；;。\n，,]|及|以及|并且|另外")
_CONTAINER = re.compile(r"(?<![A-Za-z0-9\-])([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)(?![A-Za-z0-9\-])")
_TEXT_KEYS = ("title", "description", "preconditions", "trigger", "expected", "constraints")


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _clar(spec: Dict[str, Any]) -> Dict[str, Any]:
    c = spec.get("clarifications")
    if not isinstance(c, dict):
        c = spec["clarifications"] = {"items": [], "pending_req_ids": [], "summary": ""}
    c.setdefault("items", [])
    return c


def _reqs(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in spec.get("final_requirements") or [] if isinstance(r, dict) and r.get("req_id")]


# ---------- 回答核对 ----------


def _containers(f: str) -> List[str]:
    """字段在哪些消息 / 类型里（给“规范位置”提示用）。"""
    out = [m["message"] + "." + m["path"] for m in A.other_messages_with(f, "")][:2]
    if out:
        return out
    parents = sorted(t for t, node in A._types().items() if any(k == f for k, _ in A.children(A.resolve(node))))
    return parents[:3]


def _reachable(container: str, f: str) -> Optional[bool]:
    """container（消息名或类型名）下能不能找到字段 f。认不出 container 返回 None。"""
    rn, root = A.message_root(container)
    if root is None:
        if container not in A._types():
            return None
        rn = container
    return f in A._field_index(rn)


def _expand_slashes(text: str) -> str:
    """rsrp-ThresholdMsg1-RepetitionNum2/4/8-r18 → 三个完整字段名，免得把 …Num2 当成不存在的字段。"""
    def rep(m):
        head, first, rest, tail = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        return "、".join(f"{head}{n}{tail}" for n in [first] + rest.strip("/").split("/"))
    return re.sub(r"([a-z][A-Za-z0-9\-]*?[A-Za-z])(\d+)((?:/\d+)+)(-(?:r1\d|v1\d{3}))?", rep, text)


def verify_answer(item: Dict[str, Any], answer: str) -> Dict[str, Any]:
    """按规范核对需求方的回答：提到的字段是否存在、写的位置对不对、给的取值能不能编码。

    返回 {"level": ok|corrected|reject|unchecked, "notes": [...], "rename_to", "remove", "value"}：
    reject 退回待回答；corrected 接受回答但按规范改正位置；unchecked 是规范核对不了的（行为、其它规范的说法）。"""
    out: Dict[str, Any] = {"level": "ok", "notes": [], "rename_to": "", "remove": False, "value": None}
    text = _expand_slashes(str(answer or "").strip())
    if not text:
        return {**out, "level": "reject", "notes": ["回答为空"]}
    if not A.available():
        return {**out, "level": "unchecked", "notes": ["未找到 ASN.1 IE 树，回答未做规范核对"]}
    fields = [f for f in dict.fromkeys(_IE_TOKEN.findall(text)) if f.lower() not in _NOT_IE]
    missing = []
    for f in fields:
        st = _field_status(f)
        if st["state"] == "missing" and f != item.get("field"):
            if re.search(_REMOVE.pattern + r"[^，。；]{0,12}" + re.escape(f) + "|" + re.escape(f) + r"[^，。；]{0,12}(?:" + _REMOVE.pattern + ")", text):
                continue  # 回答里说“删除 X / X 不存在”，X 本来就不该存在
            missing.append(f + (f"（近似：{'、'.join(st['near'])}）" if st.get("near") else ""))
        elif st["state"] == "renamed":
            out["notes"].append(f"{f} 的规范名是 {st['to']}，按规范名执行")
    if missing:
        out["level"] = "reject"
        out["notes"].append(f"回答里的 {'、'.join(missing)} 在 {A.spec_short()} 中不存在，请再确认")
    # 位置：一个分句里先出现的消息/类型名是容器，后面出现的字段应在它下面
    for clause in _CLAUSE.split(text):
        conts = [c for c in _CONTAINER.findall(clause) if _reachable(c, "x-never") is not None]
        if not conts:
            continue
        cont = conts[0]
        after = clause[clause.index(cont) + len(cont):]
        for f in dict.fromkeys(_IE_TOKEN.findall(after)):
            if not A.field_exists(f) or f in conts:
                continue
            ok = any(_reachable(c, f) for c in conts)
            if not ok:
                where = "、".join(_containers(f)) or "（未找到）"
                out["notes"].append(f"回答写 {f} 在 {cont} 下，按 ASN.1 不在；规范位置：{where}，按规范位置执行")
                if out["level"] == "ok":
                    out["level"] = "corrected"
    # 只有一一对应时才改需求：唯一的“改为 X”，且回答里没再提一堆别的字段（那是重新描述测试点，留给设计按回答处理）
    targets = {t for t in _RENAME.findall(text) if A.field_exists(t) and t != item.get("field")}
    known = {f for f in fields if A.field_exists(f)}
    f0 = item.get("field") or ""
    if len(targets) == 1 and len(known) <= 2:
        out["rename_to"] = targets.pop()
    elif f0 and item.get("kind") == "unknown_field" and re.search(r"(?:删除|删去|去掉|移除)[^，。；]{0,8}" + re.escape(f0), text):
        out["remove"] = True
    # 取值类问题：回答像是一个具体取值时，按 ASN.1 类型核对能不能编码
    if item.get("kind") == "value_type" and item.get("field") and A.field_exists(item["field"]):
        val = re.sub(r"^\s*" + re.escape(item["field"]) + r"\s*(?:=|为)\s*", "", text).strip()
        if len(val) <= 60 and not re.search(r"[一-鿿]{4,}", val):
            hits = A.field_hints([item["field"]], max_per_name=1)
            node = None
            if hits and hits[0]["paths"]:
                p = hits[0]["paths"][0]
                node = A.node_at(p["message"], p["path"])
            errs = [i for i in A.check_value(node, val) if i["severity"] == A.ERROR] if node is not None else []
            if errs:
                out["level"] = "reject"
                out["notes"].append(f"取值 {val} 不能按 {A.type_name(node) or '规范类型'} 编码：{errs[0]['message']}")
            else:
                out["value"] = val
    if not fields and out["level"] == "ok" and item.get("kind") in ("spec_doubt", "ambiguity", "duplicate", "inconsistent_value"):
        out["level"] = "unchecked"
        out["notes"].append("行为 / 场景类回答，规范核对不了，按需求方意见执行")
    return out


# ---------- 写回需求 ----------


def _replace_token(text: str, old: str, new: str) -> str:
    return re.sub(r"(?<![A-Za-z0-9\-])" + re.escape(old) + r"(?![A-Za-z0-9\-])", new, text)


def _rename_in_req(req: Dict[str, Any], old: str, new: str) -> List[Dict[str, Any]]:
    changes = []
    for k in _TEXT_KEYS:
        v = req.get(k)
        if isinstance(v, str) and old in v:
            nv = _replace_token(v, old, new)
            if nv != v:
                changes.append({"path": k, "before": v, "after": nv})
                req[k] = nv
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str) and old in x:
                    nx = _replace_token(x, old, new)
                    if nx != x:
                        changes.append({"path": f"{k}[{i}]", "before": x, "after": nx})
                        v[i] = nx
    pf = (req.get("acceptance") or {}).get("pass_fail")
    if isinstance(pf, list):
        for i, x in enumerate(pf):
            if isinstance(x, str) and old in x:
                nx = _replace_token(x, old, new)
                if nx != x:
                    changes.append({"path": f"acceptance.pass_fail[{i}]", "before": x, "after": nx})
                    pf[i] = nx
    for i, c in enumerate(req.get("explicit_configs") or []):
        if isinstance(c, dict) and c.get("name") == old:
            c["name"] = new
            c.setdefault("fixed_from", old)  # source_text 是需求原文，不改
            changes.append({"path": f"explicit_configs[{i}].name", "before": old, "after": new})
    return changes


def _remove_in_req(req: Dict[str, Any], field: str) -> List[Dict[str, Any]]:
    keep, changes = [], []
    for c in req.get("explicit_configs") or []:
        if isinstance(c, dict) and c.get("name") == field:
            changes.append({"path": "explicit_configs", "before": f"{field} = {c.get('value')}", "after": "（删除）"})
            continue
        keep.append(c)
    if changes:
        req["explicit_configs"] = keep
    req.setdefault("removed_fields", [])
    if field not in req["removed_fields"]:
        req["removed_fields"].append(field)
        changes.append({"path": "removed_fields", "before": "", "after": field})
    return changes


def _set_value(req: Dict[str, Any], field: str, value: Any) -> List[Dict[str, Any]]:
    changes = []
    for i, c in enumerate(req.get("explicit_configs") or []):
        if isinstance(c, dict) and c.get("name") == field and str(c.get("value")) != str(value):
            changes.append({"path": f"explicit_configs[{i}].value", "before": c.get("value"), "after": value})
            c.setdefault("value_from", c.get("value"))
            c["value"] = value
            c.pop("clarification", None)
    return changes


def _apply_item_to_req(req: Dict[str, Any], item: Dict[str, Any], v: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    f = item.get("field") or ""
    if v.get("rename_to") and f:
        out = _rename_in_req(req, f, v["rename_to"])
    elif v.get("remove") and f:
        out = _remove_in_req(req, f)
    elif v.get("value") is not None and f:
        out = _set_value(req, f, v["value"])
    for c in out:
        c.update({"req_id": req["req_id"], "clr_id": item["id"], "source": source, "at": _now()})
    return out


def apply_spec_fixes(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """规范已定的条目（只差版本后缀、枚举值写成字段、RSRP 门限写成 dBm）直接写回需求。已写回的不重复写。"""
    by_id = {r["req_id"]: r for r in _reqs(spec)}
    changes: List[Dict[str, Any]] = []
    for it in _clar(spec)["items"]:
        if it.get("status") != "resolved_by_spec" or it.get("applied") or it.get("req_id") not in by_id:
            continue
        sug = str(it.get("suggestion") or "")
        v: Dict[str, Any] = {}
        if it.get("kind") in ("renamed", "enum_as_field") and A.field_exists(sug) or it.get("kind") == "enum_as_field" and sug:
            v["rename_to"] = sug
        elif it.get("kind") == "value_type":
            m = re.match(r"^\s*" + re.escape(it.get("field") or "") + r"\s*=\s*(-?\d+)", sug)
            if m:
                v["value"] = int(m.group(1))
        if not v:
            continue
        ch = _apply_item_to_req(by_id[it["req_id"]], it, v, "规范")
        it["applied"] = True
        changes.extend(ch)
    return changes


def reapply(spec: Dict[str, Any], previous_spec: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """需求评审又跑了一轮（需求从原文重新生成）后：把已答条目的改动再写回一遍，没变的需求沿用理解确认。"""
    by_req = {r["req_id"]: r for r in _reqs(spec)}
    changes: List[Dict[str, Any]] = []
    for it in _clar(spec)["items"]:
        if it.get("status") == "resolved_by_owner" and it.get("req_id") in by_req and it.get("field"):
            src = it.get("answer_raw") or it.get("resolution") or ""
            if src.startswith("采纳建议："):
                src = str(it.get("suggestion") or "")
            v = verify_answer(it, src)
            if v["level"] != "reject":
                changes.extend(_apply_item_to_req(by_req[it["req_id"]], it, v, "需求方（沿用上一轮回答）"))
    changes.extend(apply_spec_fixes(spec))
    prev_und = (previous_spec or {}).get("understanding") or {}
    if prev_und:
        und = spec.setdefault("understanding", {})
        for rid, req in by_req.items():
            p = prev_und.get(rid) or {}
            if p.get("confirmed") and p.get("text_hash") == _restate_hash(req):
                und[rid] = dict(p)
    if changes:
        _clar(spec).setdefault("changes", []).extend(changes)
    refresh(spec)
    return changes


def _restate_hash(req: Dict[str, Any]) -> str:
    return hashlib.sha1(req_checks.restatement(req)["text"].encode("utf-8")).hexdigest()[:12]


# ---------- 状态汇总 ----------


def refresh(spec: Dict[str, Any]) -> Dict[str, Any]:
    clar = _clar(spec)
    items = clar["items"]
    pending = sorted({it["req_id"] for it in items if it.get("blocking") and it.get("status") == "open"})
    by_req: Dict[str, List[str]] = {}
    for it in items:
        by_req.setdefault(it["req_id"], []).append(it["id"])
    for req in _reqs(spec):
        rid = str(req["req_id"])
        info = req.get("clarification") if isinstance(req.get("clarification"), dict) else {}
        info.update({"status": "pending" if rid in pending else "clear", "items": by_req.get(rid, [])})
        req["clarification"] = info
    clar["pending_req_ids"] = pending
    clar["summary"] = summary_text(items, pending)
    return clar


def fingerprint(spec: Dict[str, Any]) -> str:
    reqs = [{k: v for k, v in r.items() if k != "clarification"} for r in _reqs(spec)]
    items = [(it.get("id"), it.get("status"), it.get("resolution")) for it in _clar(spec)["items"]]
    und = {k: bool((v or {}).get("confirmed")) for k, v in (spec.get("understanding") or {}).items()}
    blob = json.dumps([reqs, items, und], ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def gate_status(spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    spec = spec or {}
    items = ((spec.get("clarifications") or {}).get("items")) or []
    reqs = _reqs(spec)
    und = spec.get("understanding") or {}
    blocking_open = [it["id"] for it in items if it.get("blocking") and it.get("status") == "open"]
    unconfirmed = [r["req_id"] for r in reqs if not (und.get(r["req_id"]) or {}).get("confirmed")]
    base = spec.get("baseline") or {}
    current = fingerprint(spec) if reqs else ""
    frozen = bool(base.get("fingerprint")) and base.get("fingerprint") == current
    counts = {s: sum(1 for it in items if it.get("status") == s) for s in STATUS_LABELS}
    return {
        "counts": counts, "total": len(items), "blocking_open": blocking_open, "unconfirmed": unconfirmed,
        "requirements": len(reqs), "ready_to_freeze": not blocking_open and not unconfirmed and bool(reqs),
        "frozen": frozen, "stale": bool(base.get("fingerprint")) and not frozen,
        "baseline": {k: base.get(k) for k in ("version", "frozen_at", "confirmer", "note", "allow_pending", "pending_req_ids")} if base else None,
        "design_allowed": frozen,
    }


# ---------- 回填 ----------


def apply_answers(spec: Dict[str, Any], answers: Iterable[Dict[str, Any]], *, by: str = "",
                  confirmations: Optional[Dict[str, Any]] = None, apply_spec: bool = True) -> Dict[str, Any]:
    """answers: [{id, action: answer|accept|waive|reopen, answer, by, source}]，按 CLR 编号对回。

    返回 {"applied": [...], "rejected": [...], "skipped": [...], "changes": [...]}，spec 原地更新。"""
    clar = _clar(spec)
    items = {it["id"]: it for it in clar["items"]}
    by_req = {r["req_id"]: r for r in _reqs(spec)}
    applied, rejected, skipped, changes = [], [], [], []
    log = clar.setdefault("log", [])
    for a in answers or []:
        if not isinstance(a, dict):
            continue
        cid = str(a.get("id") or a.get("clarification_id") or "").strip()
        it = items.get(cid)
        action = str(a.get("action") or "").strip()
        action = _ACTION_BY_LABEL.get(action, action) or ("answer" if str(a.get("answer") or "").strip() else "")
        who = str(a.get("by") or by or "").strip()
        if not it:
            skipped.append({"id": cid, "reason": "澄清单里没有这个编号"})
            continue
        if not action:
            continue
        if "AI" in str(a.get("source") or ""):
            skipped.append({"id": cid, "reason": "AI 给的答案不算需求方澄清"})
            continue
        text = str(a.get("answer") or "").strip()
        if action == "reopen":
            it.update({"status": "open", "resolution": "", "verify": None})
            applied.append({"id": cid, "action": action})
        elif action == "waive":
            it.update({"status": "waived", "resolution": text or "需求方豁免：本轮不测 / 不影响设计", "answered_by": who,
                       "answered_at": _now(), "verify": None})
            applied.append({"id": cid, "action": action})
        elif action in ("answer", "accept"):
            if action == "accept":
                if not it.get("suggestion"):
                    rejected.append({"id": cid, "reason": "这条没有可采纳的建议，请直接回答"})
                    continue
                text = f"采纳建议：{it['suggestion']}" + (f"；{text}" if text else "")
            v = verify_answer(it, text if action == "answer" else str(it.get("suggestion")))
            it["verify"] = {"level": v["level"], "notes": v["notes"], "at": _now()}
            it["answer_raw"] = text
            if v["level"] == "reject":
                it.update({"status": "open", "resolution": ""})
                rejected.append({"id": cid, "reason": "；".join(v["notes"])})
                continue
            it.update({"status": "resolved_by_owner", "resolution": text, "answered_by": who, "answered_at": _now()})
            if it.get("req_id") in by_req:
                ch = _apply_item_to_req(by_req[it["req_id"]], it, v, f"需求方{('（' + who + '）') if who else ''}")
                changes.extend(ch)
            applied.append({"id": cid, "action": action, "level": v["level"], "notes": v["notes"]})
        else:
            skipped.append({"id": cid, "reason": f"不认识的处理方式 {action}"})
            continue
        log.append({"at": _now(), "by": who, "id": cid, "action": action, "answer": text[:300]})
    if confirmations:
        und = spec.setdefault("understanding", {})
        for rid, c in confirmations.items():
            if rid not in by_req:
                continue
            c = c if isinstance(c, dict) else {"confirmed": bool(c)}
            und[rid] = {"confirmed": bool(c.get("confirmed")), "by": str(c.get("by") or by or ""), "at": _now(),
                        "note": str(c.get("note") or ""), "text_hash": _restate_hash(by_req[rid])}
    if apply_spec:
        changes.extend(apply_spec_fixes(spec))
    if changes:
        clar.setdefault("changes", []).extend(changes)
        # 需求内容变了：理解确认要重新看
        und = spec.get("understanding") or {}
        for rid in {c["req_id"] for c in changes}:
            if (und.get(rid) or {}).get("confirmed"):
                und[rid]["confirmed"] = False
                und[rid]["note"] = (und[rid].get("note") or "") + "（需求已按澄清修改，请重新确认）"
    refresh(spec)
    return {"applied": applied, "rejected": rejected, "skipped": skipped, "changes": changes}


# ---------- 定稿 ----------


def freeze(spec: Dict[str, Any], *, confirmer: str, note: str = "", allow_pending: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """定稿：没有阻塞的待回答条目、每条需求的理解都确认过，才生成基线；allow_pending=True 时带着待澄清定稿（记下来）。"""
    if not str(confirmer or "").strip():
        return False, {"reason": "定稿需要填写确认人"}
    refresh(spec)
    g = gate_status(spec)
    if not g["requirements"]:
        return False, {"reason": "没有需求，不能定稿"}
    if not g["ready_to_freeze"] and not allow_pending:
        return False, {"reason": f"还有 {len(g['blocking_open'])} 条阻塞问题待回答、{len(g['unconfirmed'])} 条需求的理解未确认",
                       "gate": g}
    old = spec.get("baseline") or {}
    history = list(old.get("history") or [])
    if old.get("version"):
        history.append({k: old.get(k) for k in ("version", "frozen_at", "confirmer", "fingerprint", "allow_pending")})
    spec["baseline"] = {
        "version": int(old.get("version") or 0) + 1, "frozen_at": _now(), "confirmer": confirmer.strip(), "note": note,
        "allow_pending": bool(allow_pending and not g["ready_to_freeze"]),
        "pending_req_ids": list((spec.get("clarifications") or {}).get("pending_req_ids") or []),
        "unconfirmed": g["unconfirmed"] if allow_pending else [],
        "history": history[-20:],
    }
    spec["baseline"]["fingerprint"] = fingerprint(spec)
    return True, gate_status(spec)


# ---------- 影响分析 ----------

_ID_KEYS = ("row_id", "tc_id", "case_id", "objective_id", "id", "test_id", "bundle_id")


def _item_id(d: Dict[str, Any]) -> str:
    for k in _ID_KEYS:
        if d.get(k):
            return str(d[k])
    return ""


def _scan(obj: Any, label: str, needles: Dict[str, str], out: List[Dict[str, Any]], depth: int = 0) -> None:
    """在下游产物里找引用了受影响需求 / 改动字段的条目（有编号的 dict），记下来并标 stale。"""
    if depth > 6:
        return
    if isinstance(obj, list):
        for x in obj:
            _scan(x, label, needles, out, depth + 1)
        return
    if not isinstance(obj, dict):
        return
    iid = _item_id(obj)
    if iid and depth > 0:
        blob = json.dumps(obj, ensure_ascii=False, default=str)
        why = [desc for n, desc in needles.items() if re.search(r"(?<![A-Za-z0-9\-])" + re.escape(n) + r"(?![A-Za-z0-9\-])", blob)]
        if why:
            out.append({"artifact": label, "id": iid, "why": sorted(set(why))[:4]})
            obj["stale"] = True
            obj["stale_reason"] = "需求澄清后已修改：" + "；".join(sorted(set(why))[:3])
            return
    for k, v in obj.items():
        if isinstance(v, (list, dict)) and k not in ("stale_reason",):
            _scan(v, label, needles, out, depth + 1)


def impact(changes: List[Dict[str, Any]], *, test_design_spec: Optional[Dict[str, Any]] = None,
           test_case_spec: Optional[Dict[str, Any]] = None, exec_cases: Optional[Any] = None,
           extra_req_ids: Iterable[str] = ()) -> Dict[str, Any]:
    """澄清改动 → 受影响的需求、设计行、用例、可执行用例。下游产物原地加 stale 标记。"""
    req_ids = sorted({c["req_id"] for c in changes if c.get("req_id")} | set(extra_req_ids))
    needles: Dict[str, str] = {r: f"需求 {r}" for r in req_ids}
    for c in changes:
        if c.get("path", "").endswith(".name") or c.get("path") == "removed_fields":
            old = c.get("before") if c.get("path", "").endswith(".name") else c.get("after")
            if old and isinstance(old, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9\-]+", old):
                needles[old] = f"字段 {old}"
    hits: List[Dict[str, Any]] = []
    for label, obj in (("测试设计", test_design_spec), ("测试用例", test_case_spec), ("可执行用例", exec_cases)):
        if obj:
            _scan(obj, label, needles, hits)
    by_art: Dict[str, List[str]] = {}
    for h in hits:
        by_art.setdefault(h["artifact"], []).append(h["id"])
    return {
        "req_ids": req_ids, "hits": hits, "by_artifact": by_art,
        "plan": ([f"重新生成测试设计（受影响需求 {len(req_ids)} 条，设计行 {len(by_art.get('测试设计', []))} 个）"] if req_ids else []) +
                ([f"重新生成测试用例（{len(by_art.get('测试用例', []))} 个用例引用了改动）"] if by_art.get("测试用例") else []) +
                ([f"重新生成可执行用例（{len(by_art.get('可执行用例', []))} 个）"] if by_art.get("可执行用例") else []),
    }


# ---------- Excel 导出 / 导入 ----------

_COLUMNS = [("编号", "id", 10), ("需求ID", "req_id", 12), ("类型", "kind", 12), ("阻塞", "blocking", 6), ("状态", "status", 10),
            ("问题", "question", 60), ("依据", "evidence", 40), ("建议", "suggestion", 30), ("提出方", "raised_by", 12),
            ("需求方回答", "resolution", 50), ("处理方式", "action", 10), ("回答人", "answered_by", 10), ("核对结果", "verify", 40)]


def export_xlsx(spec: Dict[str, Any]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "需求澄清"
    ws.append([c[0] for c in _COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2F5597")
    editable = {"需求方回答", "处理方式", "回答人"}
    for it in _clar(spec)["items"]:
        verify = it.get("verify") or {}
        row = []
        for title, key, _ in _COLUMNS:
            v = it.get(key)
            if key == "kind":
                v = KIND_LABELS.get(str(v), v)
            elif key == "status":
                v = STATUS_LABELS.get(str(v), v)
            elif key == "blocking":
                v = "是" if v else ""
            elif key == "raised_by":
                v = "、".join(v or [])
            elif key == "action":
                v = ""
            elif key == "verify":
                v = "；".join(verify.get("notes") or [])
            elif key == "resolution" and it.get("status") == "resolved_by_spec":
                v = ""
            row.append("" if v is None else v)
        ws.append(row)
    dv = DataValidation(type="list", formula1='"回答,采纳建议,豁免,重开"', allow_blank=True)
    ws.add_data_validation(dv)
    col = [c[0] for c in _COLUMNS].index("处理方式") + 1
    from openpyxl.utils import get_column_letter

    dv.add(f"{get_column_letter(col)}2:{get_column_letter(col)}{max(2, ws.max_row)}")
    for i, (title, _, width) in enumerate(_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
        if title in editable:
            ws.cell(row=1, column=i).fill = PatternFill("solid", fgColor="C55A11")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B2"
    info = wb.create_sheet("说明")
    for line in ("橙色列由需求方填写：需求方回答 / 处理方式 / 回答人。按“编号”对回，其它列改了不生效。",
                 "处理方式：回答（填写回答）、采纳建议（同意“建议”列）、豁免（本轮不处理，可在回答里写原因）、重开。",
                 "处理方式留空但填了回答，按“回答”处理。规范已定的条目一般不用填。",
                 "导入后系统会再按 3GPP ASN.1 核对回答里的字段名、位置和取值，不通过的会退回待回答。"):
        info.append([line])
    info.column_dimensions["A"].width = 110
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def import_xlsx(content: bytes) -> List[Dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), data_only=True)
    ws = wb["需求澄清"] if "需求澄清" in wb.sheetnames else wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    head = [str(h or "").strip() for h in rows[0]]
    if "编号" not in head:
        raise ValueError("表头里没有“编号”列，无法按澄清编号对回")
    idx = {h: i for i, h in enumerate(head)}

    def cell(r, name):
        i = idx.get(name)
        return str(r[i]).strip() if i is not None and i < len(r) and r[i] is not None else ""

    out = []
    for r in rows[1:]:
        cid = cell(r, "编号")
        if not cid:
            continue
        ans, act, who = cell(r, "需求方回答"), cell(r, "处理方式"), cell(r, "回答人")
        if not (ans or act):
            continue
        action = _ACTION_BY_LABEL.get(act, act if act in ACTIONS else ("answer" if ans else ""))
        out.append({"id": cid, "answer": ans, "action": action, "by": who})
    return out


def view(spec: Dict[str, Any]) -> Dict[str, Any]:
    """前端需求澄清页要的全部数据。"""
    from core import spec_checkers

    refresh(spec)
    return {"requirement_spec": spec, "gate": gate_status(spec), "cards": req_checks.restatement_cards(spec),
            "coverage": spec_checkers.coverage(), "kind_labels": KIND_LABELS, "status_labels": STATUS_LABELS}
