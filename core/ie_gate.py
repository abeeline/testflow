"""IE 闸门：用例 / 可执行用例里的每条消息 IE 都按 TS 38.331 ASN.1 核对（core/asn1_paths.py）。

规则（宁可停下来问，也不输出错的信令）：
- 能确定的才自动改：路径只是漏写了中间层（nonCriticalExtension、CHOICE 分支、setup）、或者放错了父结构但
  ASN.1 里就近只有唯一一处同名字段、或者只差版本后缀（timeToTrigger → timeToTrigger-r17），并且改完后取值也合法。
  改过的 IE 记 fixed_from（原路径）和 asn1.status = fixed。
- 其余错误（规范里没有的字段、字段在别的消息里、多处可选、枚举/类型不对、“…”省略……）不猜：
  IE 标 asn1.status = error，所在用例转为“待澄清”，问题写进 open_points，交给返工或需求方确认。
"""
import re
from typing import Any, Dict, List

from core import asn1_paths as A

PENDING = "pending_clarification"


def _short(issues: List[Dict[str, str]], limit: int = 2) -> List[str]:
    return [i["message"] for i in issues if i["severity"] == A.ERROR][:limit] or [i["message"] for i in issues][:limit]


def _renames_safe(renamed: List[str]) -> bool:
    """只接受“补上版本后缀”的改名（timeToTrigger → timeToTrigger-r17）。
    去掉后缀或换成别的后缀（si-SchedulingInfo-v1700 → si-SchedulingInfo）会换成另一个版本的字段，不能自动改。"""
    for r in renamed or []:
        old, _, new = (x.strip() for x in r.partition("→"))
        if not new or not re.fullmatch(re.escape(old) + r"-[rv]\d+", new):
            return False
    return True


def check_ie(message: str, ie: Dict[str, Any], autofix: bool = True) -> Dict[str, Any]:
    """核对一条 IE，必要时就地改路径。返回写进 ie["asn1"] 的结论。"""
    path = str(ie.get("path") or "")
    value = ie.get("value")
    res = A.validate_ie(message, path, value)
    codes = {i["code"] for i in res["issues"]}
    if "UNKNOWN_MESSAGE" in codes or "NO_TREE" in codes:
        return {"status": "unchecked"}
    if res["status"] != A.ERROR:
        out: Dict[str, Any] = {"status": res["status"]}
        if res["status"] == A.WARNING:
            out["issues"] = _short(res["issues"])
        return out
    sugg = res["suggestions"][0] if res["suggestions"] else None
    fixable_codes = {"WRONG_LOCATION", "ELIDED_PATH", "MISSING_INDEX"}
    if autofix and sugg and sugg.get("unique") and not sugg.get("heuristic") and codes <= fixable_codes \
            and _renames_safe(sugg.get("renamed")):
        again = A.validate_ie(message, sugg["path"], value)
        if again["status"] != A.ERROR:
            ie.setdefault("fixed_from", path)  # 保留最初的路径（前面可能已按评审清单改过一次）
            ie["path"] = sugg["path"]
            note = f"按 {A.spec_version() or 'TS 38.331 ASN.1'} 改正路径：{sugg['display']}"
            if sugg.get("renamed"):
                note += f"（字段改名 {'；'.join(sugg['renamed'])}）"
            return {"status": "fixed", "note": note, **({"issues": _short(again["issues"])} if again["issues"] else {})}
    out = {"status": A.ERROR, "issues": _short(res["issues"], 3)}
    if res["suggestions"]:
        out["suggestions"] = [s["display"] for s in res["suggestions"][:3]]
    if res.get("elsewhere"):
        out["elsewhere"] = [f"{e['message']}.{e['path']}" for e in res["elsewhere"][:2]]
    return out


def check_messages(messages: List[Dict[str, Any]], autofix: bool = True) -> Dict[str, Any]:
    """核对一组消息（TCD 的 message_contents 或可执行用例的 message_configs），就地写 ie["asn1"]。

    返回 {errors: [文字], fixed: [文字], warnings: [文字]}。"""
    errors: List[str] = []
    fixed: List[str] = []
    warnings: List[str] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        message = str(m.get("message") or m.get("template") or "")
        label = f"{m.get('msg_id') or ''} {message}".strip()
        for ie in m.get("ies") or []:
            if not isinstance(ie, dict):
                continue
            verdict = check_ie(message, ie, autofix=autofix)
            ie["asn1"] = verdict
            if verdict["status"] == "fixed":
                fixed.append(f"{label}: {ie.get('fixed_from')} → {ie['path']}")
            elif verdict["status"] == A.ERROR:
                hint = ""
                if verdict.get("suggestions"):
                    hint = f"（候选：{'；'.join(verdict['suggestions'])}）"
                errors.append(f"{label} IE {ie.get('path')}: {'；'.join(verdict['issues'])}{hint}")
            elif verdict["status"] == A.WARNING:
                warnings.append(f"{label} IE {ie.get('path')}: {'；'.join(verdict.get('issues') or [])}")
        if str(m.get("direction") or "DL").upper() == "DL":
            paths = [str(ie.get("path")) for ie in m.get("ies") or [] if isinstance(ie, dict)
                     and (ie.get("asn1") or {}).get("status") in ("ok", "fixed", A.WARNING)]
            for w in A.missing_mandatory(message, paths) if paths else []:
                warnings.append(f"{label}: {w['message']}")
                m.setdefault("asn1_warnings", [])
                if w["message"] not in m["asn1_warnings"]:
                    m["asn1_warnings"].append(w["message"])
    return {"errors": errors, "fixed": fixed, "warnings": warnings}


def mark_pending(item: Dict[str, Any], reasons: List[str], open_points_key: str = "open_points") -> None:
    """把用例 / 可执行用例标成待澄清，并把原因写进 open_points（去重）。"""
    item["status"] = PENDING
    blocked = item.setdefault("blocked_by", [])
    ops = item.setdefault(open_points_key, [])
    for r in reasons:
        if r not in blocked:
            blocked.append(r)
        text = f"待澄清：{r}"
        if text not in ops:
            ops.append(text)


def gate_item(item: Dict[str, Any], messages_key: str, autofix: bool = True) -> Dict[str, Any]:
    """核对一条用例 / 可执行用例的全部消息 IE；有不能自动改正的错误就标成待澄清。"""
    rep = check_messages(item.get(messages_key) or [], autofix=autofix)
    if rep["errors"]:
        mark_pending(item, [f"IE 不符合 {A.spec_version() or 'TS 38.331'}：{e}" for e in rep["errors"]])
    if rep["fixed"]:
        notes = item.setdefault("review_notes", []) if messages_key == "message_contents" else item.setdefault("open_points", [])
        for f in rep["fixed"]:
            text = f"IE 路径已按 ASN.1 自动改正：{f}"
            if text not in notes:
                notes.append(text)
    return rep
