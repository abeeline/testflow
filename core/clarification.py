"""需求澄清：在测试设计之前，把需求本身的问题找出来、能用规范定的先定、定不了的挂起等需求方回答。

为什么要有这一步：需求细化稿里的 IE 名、位置、取值写错时，后面的“需求写明的配置不丢”机制会把错值原样带进
测试设计、用例和可执行用例；三方评审即使发现了，综合评审也会按“保留需求稿取值、标注待确认”放行。
这里把评审意见和 ASN.1 核对结果收成一张澄清单，每条有状态：

    resolved_by_spec   规范能给出确定答案（字段存在、位置唯一），按 ASN.1 定下来，设计直接用规范写法
    open               需要需求方回答（规范里没有的字段、取值单位/类型不对、多处可选、行为不明确）
    resolved_by_owner  需求方已回答（HITL 里用户填写的答案）

blocking=true 且 status=open 的条目会让对应需求进入“待澄清”：测试设计和用例照常起草但标为待澄清，
可执行用例不作为可执行项输出；需求写明的相关配置不再原样补进用例。
"""
import re
from typing import Any, Dict, Iterable, List, Optional

from core import asn1_paths as A

_DOUBT = re.compile(r"未能确认|无法确认|需核对|需要核对|需按\s*TS|按\s*TS[^，。；]*核对|存疑|疑为|印象|未见规范|没有这个名字|不存在|"
                    r"规范中疑|与\s*3GPP\s*规范|位置未确认|字段名|IE\s*名称|取值范围")
_MSG_WORDS = r"(SIB1|SIB2|SIB3|SIB4|SIB5|SIB19|SIB20|SIB25|MIB|RRCReconfiguration|RRCSetup|RRCResume|RRCRelease|" \
             r"UEAssistanceInformation|MeasurementReport|UECapabilityInformation)"
_CHAIN_SEP = re.compile(r"\s*(?:->|→)\s*")
_IE_TOKEN = re.compile(r"(?<![A-Za-z0-9\-])([a-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)(?![A-Za-z0-9\-])")
_TYPE_TOKEN = re.compile(r"(?<![A-Za-z0-9\-])([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)(?![A-Za-z0-9\-])")
_SUFFIX = re.compile(r"-(r1[5-9]|v1\d{3})$")
_NOT_IE = {"sub-6", "non-ntn", "e-utra", "e-utran", "ue-gnb", "x-axis", "pre-config"}


def _texts(req: Dict[str, Any], raw: str) -> List[str]:
    out = [raw] if raw else []
    for k in ("title", "description", "trigger", "expected", "constraints", "preconditions"):
        v = req.get(k)
        out.extend([str(x) for x in v] if isinstance(v, list) else [str(v)] if v else [])
    src = req.get("source") or {}
    if isinstance(src, dict):
        out.extend(str(x) for x in src.get("evidence_refs") or [])
    for c in req.get("explicit_configs") or []:
        if isinstance(c, dict):
            out.append(f"{c.get('name', '')} = {c.get('value', '')} {c.get('source_text', '')}")
    return [t for t in out if t and t.strip()]


def _sentences(text: str) -> List[str]:
    return [s for s in re.split(r"[。；;\n]", text) if s.strip()]


def raw_text_for(req_id: str, raw_requirements: Iterable[str]) -> str:
    rid = str(req_id or "")
    num = re.sub(r"^\D+", "", rid)
    for t in raw_requirements or []:
        t = str(t)
        if rid and rid in t:
            return t
        if num and re.search(rf"(?<!\d){re.escape(num)}(?!\d)", t[:200]):
            return t
    return ""


class _Builder:
    def __init__(self, answered: List[Dict[str, Any]], previous: List[Dict[str, Any]]):
        self.items: List[Dict[str, Any]] = []
        self._keys: Dict[str, Dict[str, Any]] = {}
        self.answers = {f"{a.get('req_id')}::{a.get('question')}": a for a in answered or []
                        if isinstance(a, dict) and "AI" not in str(a.get("source") or "")}  # AI 自己给的答案不算澄清
        self.previous = {f"{p.get('req_id')}::{p.get('question')}": p for p in previous or [] if isinstance(p, dict)}

    def add(self, req_id: str, kind: str, question: str, *, blocking: bool, status: str = "open", evidence: str = "",
            suggestion: str = "", raised_by: str = "ASN.1 核对", source_text: str = "", field: str = "") -> Dict[str, Any]:
        key = f"{req_id}::{kind}::{field}" if field and kind in ("unknown_field", "renamed", "value_type", "enum_as_field") \
            else f"{req_id}::{question}"
        if key in self._keys:
            item = self._keys[key]
            if raised_by not in item["raised_by"]:
                item["raised_by"].append(raised_by)
            return item
        item = {"id": "", "req_id": req_id, "kind": kind, "field": field, "question": question, "blocking": blocking,
                "status": status, "evidence": evidence, "suggestion": suggestion, "raised_by": [raised_by],
                "source_text": source_text[:300], "resolution": ""}
        qkey = f"{req_id}::{question}"
        prev = self.previous.get(qkey)
        if prev and prev.get("status") in ("resolved_by_owner", "waived"):
            item["status"], item["resolution"] = prev["status"], prev.get("resolution", "")
        ans = self.answers.get(qkey)
        if ans and str(ans.get("answer") or "").strip():
            item["status"], item["resolution"] = "resolved_by_owner", str(ans["answer"]).strip()
        self._keys[key] = item
        self.items.append(item)
        return item


def _field_status(name: str) -> Dict[str, Any]:
    """字段在规范里的情况：exists / renamed（只差版本后缀，唯一）/ missing（附近似名）。"""
    if A.field_exists(name):
        return {"state": "exists"}
    base = _SUFFIX.sub("", name)
    if base in A.enum_values():
        return {"state": "enum", "to": base, "in": A.enum_values()[base][:2]}
    variants = sorted(n for n in A._all_field_names() if _SUFFIX.sub("", n) == base and n != name)
    if len(variants) == 1:
        return {"state": "renamed", "to": variants[0]}
    import difflib

    near = difflib.get_close_matches(name, list(A._all_field_names()), n=2, cutoff=0.85)
    return {"state": "missing", "near": near}


def _paths_text(name: str, limit: int = 2) -> str:
    hits = A.field_hints([name], max_per_name=1)
    paths = hits[0]["paths"] if hits else []
    out = []
    for p in paths[:limit]:
        desc = p["type"]
        toks, _ = A.parse_path(p["path"])
        node = A.resolve(A._child_at(p["message"], toks))
        if node and node.get("t") in ("SEQ", "SET"):
            kids = [k for k, _ in A.children(node)]
            desc += "，只含：" + "、".join(kids[:10]) + (" …" if len(kids) > 10 else "")
        out.append(f"{p['message']}.{p['path']}（{desc}）")
    return "；".join(out)


def _check_chain(b: _Builder, req_id: str, chain: List[str], sentence: str) -> None:
    """需求里写的“A -> B -> C”层级：逐级核对父子关系，放错位置的按 ASN.1 给出正确位置。"""
    names = [re.sub(r"[（(].*$", "", x).strip(" ：:，,") for x in chain]
    names = [n for n in names if n]
    if len(names) < 2:
        return
    leaf = names[-1]
    m = _IE_TOKEN.search(leaf)
    if not m:
        return
    leaf = m.group(1)
    if not A.field_exists(leaf):
        return  # 不存在的字段另有条目
    idents = re.findall(r"[A-Za-z][A-Za-z0-9\-]*", names[-2])
    if not idents:
        return
    parent = idents[-1]
    types = A._types()
    if not (parent in types or A.field_exists(parent) or re.fullmatch(_MSG_WORDS, parent)):
        return  # 上一级不是类型名 / 字段名 / 消息名（普通文字），不核对
    ok = False
    if parent in types:
        ok = any(k == leaf for k, _ in A.children(types[parent]))
    else:
        for rn in ("RRCReconfiguration-IEs", "SIB1", "SIB19-r17", "SIB4", "SIB2"):
            for steps in A._field_index(rn).get(parent, [])[:3]:
                node = A._child_at(rn, A._steps_to_tokens(steps))
                if node is not None and any(k == leaf for k, _ in A.children(A._member(node) if A._is_list(node) else node)):
                    ok = True
                    break
            if ok:
                break
        if re.fullmatch(_MSG_WORDS, parent):
            rn, root = A.message_root(parent)
            ok = ok or (root is not None and any(k == leaf for k, _ in A.children(root)))
    if ok:
        return
    where = _paths_text(leaf)
    b.add(req_id, "wrong_location", f"需求写 {' -> '.join(names)}，{leaf} 不在 {parent} 下，按 ASN.1 用规范位置",
          blocking=False, status="resolved_by_spec", evidence=f"{A.spec_short()}：{where}",
          suggestion=where.split("（")[0] if where else "", raised_by="ASN.1 核对", source_text=sentence, field=leaf)


def _check_message_mentions(b: _Builder, req_id: str, sentence: str) -> None:
    """“在 SIB1 中配置 xxx-r18”：字段不在该消息里、却在别的消息里。"""
    m = re.search(_MSG_WORDS + r"\s*(?:的|中|里|内|->|→)?\s*(?:\S{0,12}?)(?:配置|下发|广播|携带|包含|添加)", sentence)
    if not m or len(set(re.findall(_MSG_WORDS, sentence))) != 1:
        return
    msg = m.group(1)
    sentence_after = sentence[m.start():]
    rn, root = A.message_root(msg)
    if root is None:
        return
    for f in dict.fromkeys(_IE_TOKEN.findall(sentence_after)):
        if not A.field_exists(f) or f in A._field_index(rn):
            continue
        elsewhere = A.other_messages_with(f, rn)
        if not elsewhere:
            continue
        loc = f"{elsewhere[0]['message']}.{elsewhere[0]['path']}"
        b.add(req_id, "wrong_message", f"需求写在 {msg} 中配置 {f}，但 {msg} 里没有这个字段，按 ASN.1 它在 {elsewhere[0]['message']}",
              blocking=False, status="resolved_by_spec", evidence=f"{A.spec_short()}：{loc}", suggestion=loc,
              source_text=sentence, field=f)


def _check_value(b: _Builder, req_id: str, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = str(cfg.get("name") or "").strip()
    if not name or not A.field_exists(name):
        return None
    hits = A.field_hints([name], max_per_name=1)
    paths = hits[0]["paths"] if hits else []
    if not paths:
        return None
    rn = paths[0]["message"]
    toks, _ = A.parse_path(paths[0]["path"])
    node = A._child_at(rn, toks)
    issues = [i for i in A.check_value(node, cfg.get("value")) if i["severity"] == A.ERROR]
    if not issues:
        return None
    dbm = re.findall(r"(?<![\d.])(-\d{2,3}(?:\.\d+)?)\s*dBm", str(cfg.get("value") or ""), re.I)
    if A.type_name(node) == "RSRP-Range" and len(set(dbm)) == 1 and 0 <= round(float(dbm[0])) + 156 <= 126:
        # 门限写成 dBm：38.331 RSRP-Range 规定门限实际值 = (IE 值 − 156) dBm，能按规范换算，不用等需求方
        idx = round(float(dbm[0])) + 156
        return b.add(req_id, "value_type", f"{name} = {cfg.get('value')} 是物理量，规范里是 RSRP-Range 索引；按 38.331 换算为 {idx}",
                     blocking=False, status="resolved_by_spec", suggestion=f"{name} = {idx}（{dbm[0]} dBm）",
                     evidence=f"{A.spec_short()}：RSRP-Range 门限实际值 = (IE 值 − 156) dBm；{paths[0]['message']}.{paths[0]['path']}",
                     source_text=str(cfg.get("source_text") or ""), field=name)
    return b.add(req_id, "value_type",
                 f"{name} = {cfg.get('value')} 与规范类型不符：{issues[0]['message']}；请给出规范编码下的取值",
                 blocking=True, evidence=f"{A.spec_short()}：{paths[0]['message']}.{paths[0]['path']}（{paths[0]['type']}）",
                 source_text=str(cfg.get("source_text") or ""), field=name)


def build_clarifications(final_requirements: List[Dict[str, Any]], *, raw_requirements: Iterable[str] = (),
                         persona_reviews: Optional[Dict[str, Any]] = None, conflicts: Optional[List[Dict[str, Any]]] = None,
                         answered: Optional[List[Dict[str, Any]]] = None,
                         previous: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """生成澄清单，并把结论写回需求（req["clarification"]、explicit_configs[].clarification）。"""
    b = _Builder(answered or [], previous or [])
    raw_list = list(raw_requirements or [])
    if not A.available():
        return {"items": [], "pending_req_ids": [], "spec_version": "", "summary": "未找到 ASN.1 IE 树，未做规范核对"}
    reqs = [r for r in final_requirements or [] if isinstance(r, dict) and r.get("req_id")]
    for req in reqs:
        rid = str(req["req_id"])
        texts = _texts(req, raw_text_for(rid, raw_list))
        blob = "\n".join(texts)
        # 1) 规范里不存在的字段
        for f in dict.fromkeys(_IE_TOKEN.findall(blob)):
            if f.lower() in _NOT_IE or not (_SUFFIX.search(f) or A.field_exists(f) or "-" in f and f[0].islower()):
                continue
            if not _SUFFIX.search(f) and not A.field_exists(f) and not re.search(r"[A-Z]", f):
                continue  # 全小写带连字符的普通词（如 sub-carrier）不当成 IE
            st = _field_status(f)
            sentence = next((s for t in texts for s in _sentences(t) if f in s), "")
            if st["state"] == "enum":
                b.add(rid, "enum_as_field", f"需求写 {f}，规范里它是枚举值 {st['to']}（字段 {'、'.join(st['in'])}），按规范写法设计",
                      blocking=False, status="resolved_by_spec", evidence=f"{A.spec_short()}：{st['to']} ∈ {'、'.join(st['in'])}",
                      suggestion=st["to"], source_text=sentence, field=f)
            elif st["state"] == "renamed":
                b.add(rid, "renamed", f"需求写 {f}，规范字段名是 {st['to']}，按规范名称设计", blocking=False,
                      status="resolved_by_spec", evidence=f"{A.spec_short()}：{_paths_text(st['to'])}",
                      suggestion=st["to"], source_text=sentence, field=f)
            elif st["state"] == "missing":
                near = f"；近似字段：{'、'.join(st['near'])}（不能直接替换）" if st["near"] else ""
                b.add(rid, "unknown_field",
                      f"{A.spec_short()} 中没有字段 {f}；请需求方给出规范出处和版本，或修改需求{near}",
                      blocking=True, evidence=f"在 {A.spec_version()} 的 ASN.1 里逐个类型查找，没有 {f}",
                      suggestion=(f"若指 {st['near'][0]}，请确认" if st["near"] else ""),
                      source_text=sentence, field=f)
        # 2) 层级写错（A -> B -> C）和消息写错（在 SIB1 中配置 X）
        for t in texts:
            for s in _sentences(t):
                if _CHAIN_SEP.search(s):
                    for seg in re.split(r"[（(]|[，,]", s):
                        parts = _CHAIN_SEP.split(seg)
                        if len(parts) >= 2:
                            _check_chain(b, rid, parts, s)
                _check_message_mentions(b, rid, s)
        # 3) 需求写明的配置：取值类型（dBm 当索引、列表当位图……）
        for cfg in req.get("explicit_configs") or []:
            if isinstance(cfg, dict):
                item = _check_value(b, rid, cfg)
                if item and item["status"] == "open":
                    cfg["clarification"] = item["question"]
    # 4) 评审意见 / 综合评审冲突里对规范的疑问
    doubts: List[tuple] = []
    for persona, label in (("spec", "规范评审"), ("carrier", "运营商评审"), ("ux", "体验评审")):
        for rv in ((persona_reviews or {}).get(persona) or {}).get("reviews") or []:
            if not isinstance(rv, dict):
                continue
            for issue in rv.get("issues") or []:
                for part in re.split(r"\n+|(?<=。)\s*(?=\d+[.、])", str(issue)):
                    if _DOUBT.search(part):
                        doubts.append((str(rv.get("req_id")), part.strip(), label))
    for c in conflicts or []:
        if isinstance(c, dict) and _DOUBT.search(f"{c.get('topic', '')}{c.get('detail', '')}"):
            doubts.append((str(c.get("req_id")), str(c.get("detail") or c.get("topic") or "").strip(), "综合评审"))
    for rid, text, label in doubts:
        if not text:
            continue
        fields = [f for f in dict.fromkeys(_IE_TOKEN.findall(text)) if f.lower() not in _NOT_IE]
        states = {f: _field_status(f) for f in fields if _SUFFIX.search(f) or A.field_exists(f)}
        missing = [f for f, st in states.items() if st["state"] == "missing"]
        known = [f for f, st in states.items() if st["state"] in ("exists", "renamed", "enum")]
        q = re.sub(r"^\d+[.、]\s*", "", text)[:240]
        if missing:
            for f in missing:
                b.add(rid, "unknown_field", f"{A.spec_short()} 中没有字段 {f}；请需求方给出规范出处和版本，或修改需求",
                      blocking=True, evidence=f"在 ASN.1 里查不到 {f}", raised_by=label, source_text=text, field=f)
        elif known and all(_paths_text(states[f].get("to") or f, 1) for f in known):
            ev = "；".join(f"{f}：{_paths_text(states[f].get('to') or f, 1)}" for f in known)
            b.add(rid, "spec_doubt", f"评审疑问：{q}", blocking=False, status="resolved_by_spec",
                  evidence=f"按 {A.spec_short()}：{ev}", raised_by=label, source_text=text)
        else:
            b.add(rid, "spec_doubt", f"评审疑问：{q}", blocking=False, raised_by=label, source_text=text,
                  evidence="ASN.1 不能回答（行为/条款类问题），请需求方确认；设计按评审建议起草并标注")
    for i, item in enumerate(b.items, start=1):
        item["id"] = f"CLR-{i:03d}"
    pending = sorted({it["req_id"] for it in b.items if it["blocking"] and it["status"] == "open"})
    by_req: Dict[str, List[str]] = {}
    for it in b.items:
        by_req.setdefault(it["req_id"], []).append(it["id"])
    for req in reqs:
        rid = str(req["req_id"])
        req["clarification"] = {"status": "pending" if rid in pending else "clear", "items": by_req.get(rid, [])}
    counts = {s: sum(1 for it in b.items if it["status"] == s) for s in ("open", "resolved_by_spec", "resolved_by_owner")}
    blocking_open = sum(1 for it in b.items if it["blocking"] and it["status"] == "open")
    return {
        "items": b.items,
        "pending_req_ids": pending,
        "spec_version": A.spec_version(),
        "summary": (f"需求澄清：{len(b.items)} 条（规范已定 {counts['resolved_by_spec']}、需求方已答 {counts['resolved_by_owner']}、"
                    f"待回答 {counts['open']}，其中阻塞 {blocking_open} 条，涉及需求 {len(pending)} 条）"),
    }


def items_for(spec: Dict[str, Any], req_ids: Iterable[str]) -> List[Dict[str, Any]]:
    ids = {str(r) for r in req_ids}
    return [it for it in ((spec or {}).get("clarifications") or {}).get("items") or [] if it.get("req_id") in ids]


def pending_ids(spec: Dict[str, Any]) -> set:
    return set(((spec or {}).get("clarifications") or {}).get("pending_req_ids") or [])


def prompt_view(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """给提示词用的精简视图：规范已定的照规范写，待回答的不要猜。"""
    out = []
    for it in items:
        out.append({k: it[k] for k in ("id", "kind", "field", "question", "status", "evidence", "suggestion", "resolution")
                    if it.get(k)})
    return out


def owner_questions(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """待需求方回答的条目，转成 HITL 的问题格式（阻塞的排在前面，不受每轮问题数上限限制）。"""
    out = []
    for it in ((spec or {}).get("clarifications") or {}).get("items") or []:
        if it.get("status") != "open" or not it.get("blocking"):
            continue  # 不阻塞的疑问照常走评审问题分级，不额外占用户的问题名额
        out.append({"req_id": it["req_id"], "question": it["question"], "priority": "P0" if it["blocking"] else "P1",
                    "needs_user": True, "ai_answer": it.get("suggestion") or "", "basis": it.get("evidence") or "",
                    "personas": it.get("raised_by") or [], "clarification_id": it["id"], "blocking": bool(it["blocking"])})
    out.sort(key=lambda q: (not q["blocking"], q["req_id"]))
    return out
