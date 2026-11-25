"""按 TS 38.331 ASN.1 逐级核对消息 IE 路径和取值。

IE 树来自 core/asn1/nr_rrc_asn1_tree.json.gz（scripts/build_rrc_asn1_tree.py 生成，版本见 spec_version()）。
测试用例、可执行用例里每条 message_contents / message_configs 的 IE 都要过这一关：

- 路径从消息根开始逐级存在（R16/R17/R18 扩展要写到 nonCriticalExtension / -v1700 这类扩展容器里）；
- 不允许“…”“...”省略，不允许“A / B”这类说明文字当路径，不允许 <占位符>；
- 枚举取值必须是 ASN.1 里的枚举值；INTEGER 取值在范围内，RSRP-Range 这类索引不能写 dBm；BIT STRING 写位串；
- 规范里不存在的字段（例如编造的 xxxExt-r18）判为错误，并给出树里能找到的候选路径。

路径写法：
    点号分隔，列表元素写 [0]/[i]，CHOICE 写出所选分支（setup / release / eventTriggered…）；
    nonCriticalExtension 可以逐级写出，也可以写成 nonCriticalExtension×5(→RRCReconfiguration-v1700-IEs)。
    开头可带消息名（RRCReconfiguration.xxx 与 xxx 等价）；RRCReconfiguration 等带 criticalExtensions 的消息，
    根节点是它的 -IEs。
"""
import difflib
import gzip
import json
import os
import re
from collections import deque
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

TREE_PATH = os.path.join(os.path.dirname(__file__), "asn1", "nr_rrc_asn1_tree.json.gz")

ERROR = "error"
WARNING = "warning"
_SEV_ORDER = {"ok": 0, WARNING: 1, ERROR: 2}

_ELIDED = re.compile(r"…|\.\.\.|⋯")
_TOKEN = re.compile(r"^(?P<name>[A-Za-z][A-Za-z0-9\-]*)(?P<idx>(\[[^\]]*\])*)$")
_REPEAT = re.compile(r"^(?P<name>[A-Za-z][A-Za-z0-9\-]*)\s*[×xX*]\s*(?P<n>\d+)$")
_ANNOT = re.compile(r"\(\s*(?:→|->)\s*(?P<type>[^)]*)\)")
_SPACE_PAREN = re.compile(r"\s+[\(（][^)）]*[\)）]")
_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")
_POWER_UNIT = re.compile(r"-?\d+(?:\.\d+)?\s*(dBm|dB)\b", re.I)
_BITSTR = re.compile(r"^(?:'?([01]+)'?B|0b([01]+)|([01]+))$")
_INT = re.compile(r"(?<![A-Za-z\d.])[-+]?\d+(?![\d.])")


@lru_cache(maxsize=1)
def _load() -> Dict[str, Any]:
    with gzip.open(TREE_PATH, "rt", encoding="utf-8") as f:
        return json.load(f)


def available() -> bool:
    return os.path.exists(TREE_PATH)


def spec_version() -> str:
    try:
        return str(_load().get("meta", {}).get("version") or "")
    except Exception:
        return ""


def spec_short() -> str:
    """消息里引用的简短版本名。"""
    v = spec_version()
    m = re.match(r"(TS 38\.331)\s*(v?\d+\.\d+\.\d+|Rel-\d+)", v)
    return f"{m.group(1)} {m.group(2)} ASN.1" if m else (v[:30] or "TS 38.331 ASN.1")


@lru_cache(maxsize=1)
def enum_values() -> Dict[str, List[str]]:
    """枚举值 → 所在字段名（用于识别把枚举值写成字段名的情况，如 sibType19-r17）。"""
    out: Dict[str, List[str]] = {}

    def visit(node, field="", depth=0):
        if not isinstance(node, dict) or depth > 60:
            return
        if node.get("t") == "ENUM":
            for e in node.get("e") or []:
                lst = out.setdefault(e, [])
                if field and field not in lst:
                    lst.append(field)
        for k, v in node.get("c") or []:
            visit(v, k, depth + 1)
        for key in ("of", "cont"):
            if node.get(key):
                visit(node[key], field, depth + 1)

    for t in _types().values():
        visit(t)
    return out


def _types() -> Dict[str, Any]:
    return _load()["types"]


def resolve(node: Optional[Dict[str, Any]], _depth: int = 0) -> Optional[Dict[str, Any]]:
    """沿 ref 找到有内容的节点；字段自身的取值/大小约束优先。"""
    if not node or _depth > 20:
        return node
    if node.get("inline") or "ref" not in node:
        return node
    target = _types().get(node["ref"])
    if target is None:
        return node
    out = dict(resolve(target, _depth + 1) or {})
    for k in ("rng", "sz", "opt", "def"):
        if k in node:
            out[k] = node[k]
    out["_ref"] = node["ref"]
    return out


def type_name(node: Optional[Dict[str, Any]]) -> str:
    if not node:
        return ""
    return str(node.get("ref") or node.get("_ref") or "")


def children(node: Optional[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    n = resolve(node)
    if not n:
        return []
    if n.get("t") == "OCT_STR" and n.get("cont"):
        return children(n["cont"])
    return [(k, v) for k, v in n.get("c") or []]


def _child(node, name) -> Optional[Dict[str, Any]]:
    for k, v in children(node):
        if k == name:
            return v
    return None


def _is_list(node) -> bool:
    n = resolve(node)
    return bool(n) and n.get("t") in ("SEQ_OF", "SET_OF")


def _member(node) -> Optional[Dict[str, Any]]:
    n = resolve(node)
    return n.get("of") if n else None


def _setup_release(node) -> Optional[Dict[str, Any]]:
    """SetupRelease 实例：返回 setup 分支，否则 None。"""
    n = resolve(node)
    if not n or n.get("t") != "CHOICE":
        return None
    names = [k for k, _ in n.get("c") or []]
    if sorted(names) == ["release", "setup"]:
        return _child(n, "setup")
    return None


# ---------- 消息根 ----------


def message_root(message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """消息名 → (根类型名, 根节点)。RRCReconfiguration → RRCReconfiguration-IEs；SIB19 → SIB19-r17。"""
    types = _types()
    msg = re.sub(r"\s+", "", str(message or ""))
    msg = re.sub(r"[（(].*$", "", msg)
    if not msg:
        return "", None
    candidates = [msg] + [f"{msg}-r{r}" for r in (16, 17, 18, 19)]
    m = re.match(r"^(SIB|PosSIB)(\d+)$", msg, re.I)
    if m:
        candidates += [f"SIB{m.group(2)}-r{r}" for r in (16, 17, 18, 19)]
    for cand in candidates:
        if cand in types:
            node = types[cand]
            if _child(node, "criticalExtensions") is not None and f"{cand}-IEs" in types:
                return f"{cand}-IEs", types[f"{cand}-IEs"]
            return cand, node
    return "", None


# ---------- 路径解析 ----------


def _split_path(path: str) -> List[str]:
    """按点号切分，忽略圆括号/尖括号内的点。"""
    out, buf, depth = [], [], 0
    for ch in path:
        if ch in "([<（{":
            depth += 1
        elif ch in ")]>）}" and depth:
            depth -= 1
        if ch == "." and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def parse_path(path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """→ (tokens, issues)。token: {name, idx: [..], annot}；格式问题直接成 issue。"""
    issues: List[Dict[str, str]] = []
    raw = str(path or "").strip()
    if not raw:
        return [], [_issue(ERROR, "EMPTY_PATH", "IE 路径为空")]
    if _ELIDED.search(raw):
        issues.append(_issue(ERROR, "ELIDED_PATH", "路径中用了“…”省略，无法逐级核对；请从消息根写出完整路径"))
        raw = _ELIDED.sub(".", raw)
    if re.search(r"\s/\s|／|、", raw):
        return [], issues + [_issue(ERROR, "NOT_A_PATH", "这不是字段路径（含“/”或说明文字）；每条 IE 只写一个完整路径")]
    if re.search(r"<[^>]*>", raw):
        issues.append(_issue(ERROR, "PLACEHOLDER", "路径里有 <占位符>，需写成具体的字段和下标"))
        raw = re.sub(r"<[^>]*>", "PLACEHOLDER", raw)
    raw = _SPACE_PAREN.sub("", raw)
    tokens: List[Dict[str, Any]] = []
    for part in _split_path(raw):
        part = part.strip()
        if not part:
            continue
        annot = ""
        m = _ANNOT.search(part)
        if m:
            annot = m.group("type").strip()
            part = _ANNOT.sub("", part).strip()
        part = re.sub(r"\([^)]*\)$", "", part).strip()
        rep = _REPEAT.match(part)
        if rep:
            n = int(rep.group("n"))
            tokens.extend({"name": rep.group("name"), "idx": [], "annot": ""} for _ in range(n - 1))
            tokens.append({"name": rep.group("name"), "idx": [], "annot": annot})
            continue
        tm = _TOKEN.match(part)
        if not tm:
            issues.append(_issue(ERROR, "BAD_TOKEN", f"“{part}”不是合法的字段名"))
            tokens.append({"name": part, "idx": [], "annot": annot, "bad": True})
            continue
        idx = re.findall(r"\[([^\]]*)\]", tm.group("idx") or "")
        tokens.append({"name": tm.group("name"), "idx": idx, "annot": annot})
    return tokens, issues


def _issue(sev: str, code: str, msg: str) -> Dict[str, str]:
    return {"severity": sev, "code": code, "message": msg}


def _render(tokens: List[Dict[str, Any]], root_name: str = "", compact: bool = True) -> str:
    parts: List[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if compact and t["name"] == "nonCriticalExtension":
            j = i
            while j + 1 < len(tokens) and tokens[j + 1]["name"] == "nonCriticalExtension":
                j += 1
            n = j - i + 1
            label = "nonCriticalExtension" + (f"×{n}" if n > 1 else "")
            if tokens[j].get("type"):
                label += f"(→{tokens[j]['type']})"
            parts.append(label)
            i = j + 1
            continue
        parts.append(t["name"] + "".join(f"[{x}]" for x in t.get("idx") or []))
        i += 1
    return ".".join(parts)


def _walk(root: Dict[str, Any], tokens: List[Dict[str, Any]]):
    """逐级走。返回 (走到的节点, 已走 token(带 type), 失败位置 or None, issues)。"""
    node = root
    walked: List[Dict[str, Any]] = []
    issues: List[Dict[str, str]] = []
    for i, tok in enumerate(tokens):
        if tok.get("bad") or tok["name"] == "PLACEHOLDER":
            return node, walked, i, issues
        nxt = _child(node, tok["name"])
        implicit_setup = False
        if nxt is None:
            setup = _setup_release(node)
            if setup is not None and _child(setup, tok["name"]) is not None:
                walked.append({"name": "setup", "idx": [], "type": type_name(setup)})
                node, nxt, implicit_setup = setup, _child(setup, tok["name"]), True
        if nxt is None:
            if _is_list(node) and walked:
                issues.append(_issue(ERROR, "MISSING_INDEX", f"{walked[-1]['name']} 是列表，需要写下标（如 [0]）"))
            return node, walked, i, issues
        if implicit_setup:
            issues.append(_issue(WARNING, "IMPLICIT_SETUP", f"{walked[-2]['name'] if len(walked) > 1 else ''} 是 SetupRelease，路径应写出 .setup"))
        rec = {"name": tok["name"], "idx": list(tok["idx"]), "type": type_name(nxt)}
        if tok.get("annot"):
            got = type_name(nxt)
            if got and not got.endswith(tok["annot"]) and tok["annot"] not in got:
                issues.append(_issue(ERROR, "WRONG_CONTAINER",
                                     f"{tok['name']} 实际是 {got}，不是 {tok['annot']}（nonCriticalExtension 层数不对）"))
        node = nxt
        for _ in tok["idx"]:
            if not _is_list(node):
                issues.append(_issue(ERROR, "NOT_A_LIST", f"{tok['name']} 不是列表，不能写下标"))
                break
            node = _member(node)
        walked.append(rec)
        # 列表后面直接接子字段（漏了下标）
        if not tok["idx"] and _is_list(node) and i + 1 < len(tokens):
            issues.append(_issue(WARNING, "MISSING_INDEX", f"{tok['name']} 是列表，子字段前应写下标（如 [0]）"))
            rec["idx"] = ["0"]
            node = _member(node)
    return node, walked, None, issues


# ---------- 候选路径（字段不在写的位置时，到消息树里找） ----------

# 走这些分支才能到的位置一般不是测试想配的地方（辅小区组、专用 SIB 下发、侧行链路……），排序时靠后
_DETOUR = re.compile(r"^(secondaryCellGroup|sCellToAddModList|sCellConfigCommon|mrdc-|nr-SCG|dedicatedSystemInformationDelivery|"
                     r"dedicatedSIB1-Delivery|dedicatedPosSysInfoDelivery|sl-|sCellSIB20|criticalExtensions|"
                     r"lateNonCriticalExtension|appLayer|ltm-|scg-|nr-SecondaryCellGroupConfig|cg-Config|ue-|t316|"
                     r"conditionalReconfiguration|daps)", re.I)


def _cost(name: str) -> int:
    return 25 if _DETOUR.match(name) else 1


@lru_cache(maxsize=64)
def _field_index(root_name: str) -> Dict[str, List[Tuple[Tuple[str, ...], ...]]]:
    """消息根下每个字段名 → 从根到它的路径列表。每个命名类型只展开一次（代价最小的那条路），
    辅小区组、专用 SIB 下发这类绕路的分支代价高，排在后面。"""
    import heapq

    root = _types().get(root_name)
    index: Dict[str, List[Tuple[int, Tuple[Tuple[str, ...], ...]]]] = {}
    if root is None:
        return {}
    expanded = {root_name}
    counter = 0
    heap: List[Any] = [(0, counter, root, (), ())]
    while heap:
        cost, _, node, path, refs = heapq.heappop(heap)
        if refs:
            if any(r in expanded for r in refs):
                continue  # 这个类型已经从更便宜的路径展开过
            expanded.update(refs)
        if len(path) > 40:
            continue
        for name, child in children(node):
            idx: Tuple[str, ...] = ()
            target = child
            n = resolve(child)
            if n and n.get("t") in ("SEQ_OF", "SET_OF"):
                idx = ("0",)
                target = n.get("of")
            step = path + ((name,) + idx,)
            index.setdefault(name, []).append((cost + _cost(name), step))
            if target is None:
                continue
            crefs = [type_name(target)] if not target.get("inline") else []
            tn = resolve(target)
            if tn and tn.get("t") == "OCT_STR" and tn.get("cont"):
                crefs.append(type_name(tn["cont"]))
            crefs = tuple(r for r in crefs if r)
            if crefs and any(r in expanded for r in crefs):
                continue
            counter += 1
            heapq.heappush(heap, (cost + _cost(name), counter, target, step, crefs))
    return {k: [s for _, s in sorted(v, key=lambda x: (x[0], len(x[1])))] for k, v in index.items()}


def _steps_to_tokens(steps) -> List[Dict[str, Any]]:
    return [{"name": s[0], "idx": list(s[1:]), "annot": ""} for s in steps]


def _find_below(node: Dict[str, Any], name: str, max_depth: int = 9) -> List[List[Dict[str, Any]]]:
    """在 node 子树里按层找字段 name，返回最浅一层的全部相对路径（token 列表）。绕路分支只在找不到时才看。"""
    for allow_detour in (False, True):
        frontier: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = [(node, [])]
        seen: set = set()
        for _ in range(max_depth):
            hits: List[List[Dict[str, Any]]] = []
            nxt: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
            for cur, rel in frontier:
                for cname, child in children(cur):
                    if not allow_detour and _DETOUR.match(cname):
                        continue
                    n = resolve(child)
                    is_list = bool(n) and n.get("t") in ("SEQ_OF", "SET_OF")
                    tok = {"name": cname, "idx": ["0"] if is_list else [], "annot": ""}
                    if cname == name:
                        hits.append(rel + [tok])
                        continue
                    target = n.get("of") if is_list else child
                    if target is None:
                        continue
                    key = type_name(target)
                    if key:
                        if key in seen:
                            continue
                        seen.add(key)
                    nxt.append((target, rel + [tok]))
            if hits:
                return hits
            frontier = nxt
            if not frontier:
                break
    return []


def _release_variants(name: str, names: List[str]) -> List[str]:
    """同一个字段换了版本后缀（timeToTrigger ↔ timeToTrigger-r17）。"""
    base = re.sub(r"-(r1[5-9]|v1\d{3})$", "", name)
    return [n for n in names if n != name and re.sub(r"-(r1[5-9]|v1\d{3})$", "", n) == base]


def _base(name: str) -> str:
    return re.sub(r"-(r1[5-9]|v1\d{3})$", "", name).lower()


def _context_score(rel: List[Dict[str, Any]], dropped: List[str]) -> float:
    if not dropped:
        return 0.0
    total = 0.0
    for t in rel:
        total += max(difflib.SequenceMatcher(None, _base(t["name"]), _base(d)).ratio() for d in dropped)
    return total


def _nodes_along(root: Dict[str, Any], walked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = [root]
    node = root
    for rec in walked:
        node = _child(node, rec["name"])
        if node is None:
            break
        for _ in rec.get("idx") or []:
            if _is_list(node):
                node = _member(node)
        out.append(node)
    return out


def repair(root_name: str, tokens: List[Dict[str, Any]], max_steps: int = 8) -> Dict[str, Any]:
    """把写错位置的路径按 ASN.1 修到正确位置：
    1) 失败处的同级有只差版本后缀的字段 → 改名；
    2) 否则从失败处往上逐级在子树里找同名字段，找到最近的一处就接上（保留用户写的上下文和下标）；
    3) 同一层找到多处 → 用后面的路径能否走通来排除，仍有多处就算歧义，不自动改。
    返回 {status: fixed|ambiguous|not_found, tokens, candidates, renamed}。"""
    root = _types().get(root_name)
    cur = [dict(t) for t in tokens]
    renamed: List[str] = []
    heuristic = False
    for _ in range(max_steps):
        node, walked, fail, _ = _walk(root, cur)
        if fail is None:
            return {"status": "fixed", "tokens": [{"name": w["name"], "idx": w["idx"], "annot": ""} for w in walked],
                    "walked": walked, "renamed": renamed, "candidates": [], "heuristic": heuristic}
        tok = cur[fail]
        if tok.get("bad") or tok["name"] == "PLACEHOLDER":
            return {"status": "not_found", "candidates": [], "renamed": renamed}
        here = [k for k, _ in children(node)]
        setup = _setup_release(node)
        if setup is not None:
            here += [k for k, _ in children(setup)]
        variants = _release_variants(tok["name"], here)
        if len(variants) == 1:
            renamed.append(f"{tok['name']} → {variants[0]}")
            cur[fail] = {**tok, "name": variants[0]}
            continue
        nodes = _nodes_along(root, walked)
        prefix_tokens = [{"name": w["name"], "idx": list(w["idx"]), "annot": ""} for w in walked]
        found = None
        for k in range(len(nodes) - 1, -1, -1):
            rels = _find_below(nodes[k], tok["name"])
            if rels:
                found = (k, rels)
                break
        if not found:
            return {"status": "not_found", "candidates": [], "renamed": renamed}
        k, rels = found
        options = []
        for rel in rels:
            rel = [dict(t) for t in rel]
            if tok["idx"]:
                rel[-1]["idx"] = list(tok["idx"])
            cand = prefix_tokens[:k] + rel + [dict(t) for t in cur[fail + 1:]]
            _, w2, f2, _ = _walk(root, cand)
            options.append((f2 is None, cand))
        good = [c for ok, c in options if ok] or [c for _, c in options]
        if len(good) > 1:
            # 用原路径里被替换掉的那几级做参照（如 am.dl-AM-RLC → dl-AM-RLC-v1700），明显更像的那个胜出
            dropped = [t["name"] for t in cur[k:fail]] + [t["name"] for t in walked[k:]]
            scored = sorted(((_context_score(c[k:], dropped), i) for i, c in enumerate(good)), reverse=True)
            if dropped and scored[0][0] > 0 and scored[0][0] - scored[1][0] >= 0.08:
                good = [good[scored[0][1]]]
                heuristic = True
        if len(good) > 1:
            cands = []
            for c in good[:4]:
                _, w3, f3, _ = _walk(root, c)
                cands.append(_render(w3 if f3 is None else [], root_name))
            return {"status": "ambiguous", "candidates": [x for x in cands if x], "renamed": renamed}
        cur = good[0]
    return {"status": "not_found", "candidates": [], "renamed": renamed}


def suggest(root_name: str, tokens: List[Dict[str, Any]], fail_at: int, max_n: int = 3) -> List[Dict[str, Any]]:
    """字段不在写的位置时给候选路径：先按 repair() 就近修复，再在整棵消息树里找同名 / 近似名字段。"""
    if root_name not in _types() or fail_at >= len(tokens):
        return []
    out: List[Dict[str, Any]] = []
    rep = repair(root_name, tokens)
    if rep["status"] == "fixed":
        out.append({"path": _render(rep["walked"], root_name, compact=False),
                    "display": _render(rep["walked"], root_name), "exact_name": not rep["renamed"],
                    "renamed": rep["renamed"], "unique": True, "heuristic": rep.get("heuristic", False), "field": tokens[fail_at]["name"]})
        return out
    if rep["status"] == "ambiguous":
        for c in rep["candidates"]:
            out.append({"path": c, "display": c, "exact_name": True, "unique": False, "field": tokens[fail_at]["name"]})
        return out[:max_n]
    index = _field_index(root_name)
    name = tokens[fail_at]["name"]
    names = [(n, False) for n in difflib.get_close_matches(name, list(index.keys()), n=4, cutoff=0.75) if n != name]
    root = _types()[root_name]
    for cand_name, exact in names:
        for steps in index.get(cand_name, [])[:2]:
            base = _steps_to_tokens(steps)
            _, walked, fail, _ = _walk(root, base)
            if fail is None:
                out.append({"path": _render(walked, root_name, compact=False), "display": _render(walked, root_name),
                            "exact_name": False, "unique": False, "field": cand_name})
    return out[:max_n]


_OTHER_ROOTS = ("SIB1", "SIB19", "SIB2", "SIB3", "SIB4", "SIB5", "SIB20", "SIB25", "RRCReconfiguration", "RRCSetup",
                "RRCResume", "RRCRelease", "UEAssistanceInformation", "MeasurementReport", "UECapabilityInformation")


def other_messages_with(name: str, exclude_root: str) -> List[Dict[str, str]]:
    """字段不在这条消息里时，看看它在哪些消息里（例如写在 SIB1 里、实际在 SIB19）。"""
    out = []
    for m in _OTHER_ROOTS:
        rn, r = message_root(m)
        if r is None or rn == exclude_root:
            continue
        paths = _field_index(rn).get(name) or []
        if paths:
            _, walked, fail, _ = _walk(r, _steps_to_tokens(paths[0]))
            if fail is None:
                out.append({"message": rn, "path": _render(walked, rn)})
    return out


# ---------- 取值 ----------


def _enum_like(token: str, enum: List[str]) -> bool:
    m = re.match(r"^([A-Za-z]+)", token)
    if not m or len(m.group(1)) < 2 or not re.search(r"\d", token):
        return False
    prefix = m.group(1)
    return any(e.startswith(prefix) for e in enum)


def check_value(node: Optional[Dict[str, Any]], value: Any) -> List[Dict[str, str]]:
    v = str(value if value is not None else "").strip()
    if not v or node is None:
        return []
    n = resolve(node)
    if not n:
        return []
    t = n.get("t")
    if t == "CHOICE":
        alts = [k for k, _ in n.get("c") or []]
        if v in alts or any(v.startswith(a) for a in alts):
            return []
        setup = _setup_release(n)
        if setup is not None:
            return check_value(setup, v)
        return [_issue(WARNING, "VALUE_NOT_CONCRETE", f"这是 CHOICE（{', '.join(alts[:6])}），取值应写所选分支和子字段")]
    if t == "ENUM":
        enum = list(n.get("e") or [])
        toks = _IDENT.findall(v)
        bad = [x for x in toks if x not in enum and (_enum_like(x, enum) or (len(toks) == 1 and re.fullmatch(_IDENT, v)))]
        if bad:
            return [_issue(ERROR, "BAD_ENUM", f"{'、'.join(bad)} 不是枚举值；可选：{', '.join(enum[:16])}{' …' if len(enum) > 16 else ''}")]
        if not any(x in enum for x in toks):
            return [_issue(WARNING, "VALUE_NOT_CONCRETE", f"没有给出具体枚举值；可选：{', '.join(enum[:16])}{' …' if len(enum) > 16 else ''}")]
        return []
    if t == "INT":
        rng = n.get("rng") or [None, None]
        label = f"INTEGER ({rng[0]}..{rng[1]})" + (f"，类型 {type_name(node)}" if type_name(node) else "")
        if _POWER_UNIT.search(v):
            return [_issue(ERROR, "UNIT_MISMATCH", f"{label} 是编码值/索引，不能直接写 dBm/dB 物理量；请按映射表换算成索引")]
        nums = [int(x) for x in _INT.findall(v)]
        if not nums:
            if v.lower() in ("setup", "release"):
                return []
            return [_issue(WARNING, "VALUE_NOT_CONCRETE", f"{label}：取值不是具体整数")]
        out_of = [x for x in nums if (rng[0] is not None and x < rng[0]) or (rng[1] is not None and x > rng[1])]
        if out_of:
            return [_issue(ERROR, "OUT_OF_RANGE", f"{', '.join(map(str, out_of))} 超出 {label}")]
        # “T0 + 30s”“当前 UTC + 600s”这类表达式里也有数字，但不是能直接编码的整数；括号里的说明不算
        core = re.sub(r"[（(][^（）()]*[）)]", "", v).strip()
        if not re.fullmatch(r"[-+]?\d+(\s*[,，、/]\s*[-+]?\d+)*", core):
            return [_issue(WARNING, "VALUE_NOT_CONCRETE", f"{label}：取值是表达式或说明（{v[:30]}），执行前要换成具体整数")]
        return []
    if t == "BIT_STR":
        sz = n.get("sz")
        label = "BIT STRING" + (f" (SIZE {sz[0]}{'' if sz[0] == sz[1] else '..' + str(sz[1])})" if sz else "")
        compact = re.sub(r"\s+", "", v)
        hx = re.match(r"^(?:0x([0-9A-Fa-f]+)|'([0-9A-Fa-f]+)'H)$", compact)
        if hx:
            nbits = len(hx.group(1) or hx.group(2)) * 4
            if sz and sz[1] is not None and nbits - 3 > sz[1]:
                return [_issue(ERROR, "BAD_BITSTRING", f"{label}：十六进制位数 {nbits} 超出")]
            return []
        m = _BITSTR.match(compact)
        if not m:
            if n.get("named") and all(x in n["named"] for x in _IDENT.findall(v)):
                return []
            if re.search(r"[\u4e00-\u9fff]", v) and not re.search(r"[{｛]", v):
                return [_issue(WARNING, "VALUE_NOT_CONCRETE", f"{label}：只有文字描述，执行前要换成具体位串")]
            return [_issue(ERROR, "BAD_BITSTRING", f"{label}：应写位串（如 '0101'B），不是列表或枚举")]
        bits = next(g for g in m.groups() if g)
        if sz and ((sz[0] is not None and len(bits) < sz[0]) or (sz[1] is not None and len(bits) > sz[1])):
            return [_issue(ERROR, "BAD_BITSTRING", f"{label}：位数 {len(bits)} 不对")]
        return []
    if t == "BOOL":
        if v.lower() not in ("true", "false"):
            return [_issue(ERROR, "BAD_BOOL", "BOOLEAN 只能是 true / false")]
    return []


# ---------- 对外接口 ----------


def validate_ie(message: str, path: str, value: Any = None) -> Dict[str, Any]:
    """核对一条 IE。返回 {status: ok|warning|error, issues, canonical, display, suggestions, root, spec_version}。"""
    result: Dict[str, Any] = {"status": "ok", "issues": [], "canonical": "", "display": "", "suggestions": [],
                              "root": "", "spec_version": spec_version()}
    if not available():
        result["status"] = WARNING
        result["issues"].append(_issue(WARNING, "NO_TREE", "未找到 ASN.1 IE 树，无法核对"))
        return result
    root_name, root = message_root(message)
    result["root"] = root_name
    if root is None:  # NAS / MAC CE 等不在 38.331 里的消息不核对
        result["issues"].append(_issue(WARNING, "UNKNOWN_MESSAGE", f"{message} 不在 38.331 ASN.1 里（非 RRC 消息不核对）"))
        return _finish(result)
    tokens, issues = parse_path(path)
    result["issues"].extend(issues)
    # 开头的消息名 / 根类型名 / criticalExtensions 前缀
    msg_names = {str(message).strip(), root_name, root_name[:-4] if root_name.endswith("-IEs") else root_name}
    while tokens and tokens[0]["name"] in msg_names and not tokens[0]["idx"]:
        tokens = tokens[1:]
    if len(tokens) >= 2 and tokens[0]["name"] == "criticalExtensions":
        tokens = tokens[2:]
    if not tokens:
        if not result["issues"]:
            result["issues"].append(_issue(ERROR, "EMPTY_PATH", "只有消息名，没有字段"))
        return _finish(result)
    node, walked, fail, walk_issues = _walk(root, tokens)
    result["issues"].extend(walk_issues)
    if fail is not None:
        tok = tokens[fail]
        where = _render(walked, root_name, compact=True) or root_name
        if not (tok.get("bad") or tok["name"] == "PLACEHOLDER"):
            sugg = suggest(root_name, tokens, fail)
            result["suggestions"] = sugg
            if tok["name"] in _field_index(root_name):
                msg = f"{tok['name']} 不在 {where} 下"
                if sugg and sugg[0].get("unique"):
                    msg += f"；按 ASN.1 应为 {sugg[0]['display']}"
                elif sugg:
                    msg += f"；ASN.1 里有多处：{'；'.join(s['display'] for s in sugg)}，需按测试意图选定"
                result["issues"].append(_issue(ERROR, "WRONG_LOCATION", msg))
            else:
                elsewhere = other_messages_with(tok["name"], root_name)
                if elsewhere:
                    result["elsewhere"] = elsewhere
                    result["issues"].append(_issue(ERROR, "WRONG_MESSAGE",
                        f"{tok['name']} 不在 {root_name} 里，在 {elsewhere[0]['message']}.{elsewhere[0]['path']}"
                        "（要换消息，测试流程需要相应调整）"))
                    result["suggestions"] = []
                else:
                    msg = f"{root_name} 里没有字段 {tok['name']}（{spec_version() or 'ASN.1'}）"
                    close = [s for s in sugg if not s["exact_name"]]
                    near = difflib.get_close_matches(tok["name"], list(_all_field_names()), n=1, cutoff=0.85)
                    near_else = other_messages_with(near[0], root_name) if near and near[0] not in _field_index(root_name) else []
                    if near_else:
                        result["elsewhere"] = near_else
                        msg += (f"；近似字段 {near[0]} 在 {near_else[0]['message']}.{near_else[0]['path']}"
                                "（仅供参考，不能自动替换）")
                    elif close:
                        msg += f"；近似字段：{close[0]['display']}（仅供参考，不能自动替换）"
                    msg += "；不能编造字段，需要需求方给出规范出处或修改用例"
                    result["issues"].append(_issue(ERROR, "UNKNOWN_FIELD", msg))
        return _finish(result)
    result["canonical"] = _render(walked, root_name, compact=False)
    result["display"] = _render(walked, root_name, compact=True)
    result["issues"].extend(check_value(node, value))
    return _finish(result)


def _finish(result: Dict[str, Any]) -> Dict[str, Any]:
    worst = "ok"
    for it in result["issues"]:
        if _SEV_ORDER[it["severity"]] > _SEV_ORDER[worst]:
            worst = it["severity"]
    result["status"] = worst
    return result


def missing_mandatory(message: str, paths: List[str]) -> List[Dict[str, str]]:
    """同一条消息里新建的列表元素 / R16+ 扩展结构，必选子字段一个都没写时提示。"""
    root_name, root = message_root(message)
    if root is None:
        return []
    walked_paths: List[List[Dict[str, Any]]] = []
    for p in paths:
        tokens, _ = parse_path(p)
        while tokens and tokens[0]["name"] in {message, root_name}:
            tokens = tokens[1:]
        _, walked, fail, _ = _walk(root, tokens)
        if fail is None and walked:
            walked_paths.append(walked)
    keys = {}
    for walked in walked_paths:
        for depth in range(1, len(walked)):
            prefix = tuple((t["name"], tuple(t["idx"])) for t in walked[:depth])
            keys.setdefault(prefix, set()).add(walked[depth]["name"])
    out = []
    for prefix, used in keys.items():
        last_name, last_idx = prefix[-1]
        if not last_idx and not re.search(r"-r1[6-9]$", last_name):
            continue
        node = root
        toks = [{"name": n, "idx": list(i), "annot": ""} for n, i in prefix]
        node, _, fail, _ = _walk(root, toks)
        if fail is not None:
            continue
        setup = _setup_release(node)
        if setup is not None:
            continue
        mand = [k for k, v in children(node) if not v.get("opt") and k not in used]
        if mand:
            out.append(_issue(WARNING, "MISSING_MANDATORY",
                              f"{_render([{'name': n, 'idx': list(i)} for n, i in prefix])} 缺少必选字段：{', '.join(mand)}"))
    return out


def field_hints(names: List[str], messages: List[str] = None, max_per_name: int = 3) -> List[Dict[str, Any]]:
    """给提示词用：字段名 → 在各消息里的规范路径和类型（让模型照抄，而不是凭记忆写）。"""
    if not available():
        return []
    roots = []
    for m in messages or ["RRCReconfiguration", "SIB1", "SIB19", "SIB4", "SIB2", "SIB3", "RRCSetup", "RRCResume",
                          "UEAssistanceInformation", "MeasurementReport", "RRCReconfigurationComplete"]:
        rn, r = message_root(m)
        if r is not None and rn not in roots:
            roots.append(rn)
    out = []
    for name in dict.fromkeys(n for n in names if n):
        hits = []
        for rn in roots:
            for steps in _field_index(rn).get(name, [])[:max_per_name]:
                toks = _steps_to_tokens(steps)
                _, walked, fail, _ = _walk(_types()[rn], toks)
                if fail is not None:
                    continue
                n = resolve(_child_at(rn, toks))
                hits.append({"message": rn, "path": _render(walked, rn), "type": _describe(n)})
        out.append({"field": name, "found": bool(hits), "paths": hits[:max_per_name * 2]})
    return out


def node_at(message: str, path: str) -> Optional[Dict[str, Any]]:
    """按路径取到字段节点（路径不合法返回 None）。"""
    if not available():
        return None
    root_name, root = message_root(message)
    if root is None:
        return None
    tokens, issues = parse_path(path)
    if any(i["severity"] == ERROR for i in issues):
        return None
    msg_names = {str(message).strip(), root_name, root_name[:-4] if root_name.endswith("-IEs") else root_name}
    while tokens and tokens[0]["name"] in msg_names and not tokens[0]["idx"]:
        tokens = tokens[1:]
    if not tokens:
        return None
    node, _, fail, _ = _walk(root, tokens)
    return node if fail is None else None


def _child_at(root_name: str, toks: List[Dict[str, Any]]):
    node, _, fail, _ = _walk(_types()[root_name], toks)
    return node if fail is None else None


def _describe(n: Optional[Dict[str, Any]]) -> str:
    if not n:
        return ""
    t = n.get("t")
    if t == "ENUM":
        e = n.get("e") or []
        return "ENUMERATED {" + ", ".join(e[:12]) + (" …" if len(e) > 12 else "") + "}"
    if t == "INT":
        r = n.get("rng") or [None, None]
        return f"INTEGER ({r[0]}..{r[1]})" + (f" [{n['_ref']}]" if n.get("_ref") else "")
    if t == "BIT_STR":
        s = n.get("sz")
        return "BIT STRING" + (f" (SIZE {s[0]}{'' if s[0] == s[1] else '..' + str(s[1])})" if s else "")
    if t == "CHOICE":
        return "CHOICE {" + ", ".join(k for k, _ in n.get("c") or []) + "}"
    if t in ("SEQ_OF", "SET_OF"):
        return "SEQUENCE OF"
    if t == "SEQ":
        return "SEQUENCE" + (f" [{n['_ref']}]" if n.get("_ref") else "")
    return str(t)


def mentioned_fields(text: str) -> List[str]:
    """从需求原文里抽出像 38.331 字段名的词（带 -r1x / -v1xxx 后缀或驼峰带连字符），只保留树里存在或带版本后缀的。"""
    out = []
    for tok in re.findall(r"[a-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+", str(text or "")):
        if re.search(r"-(r1[5-9]|v1\d{3})$", tok) or _looks_like_field(tok):
            out.append(tok)
    return list(dict.fromkeys(out))


@lru_cache(maxsize=1)
def _all_field_names() -> frozenset:
    names = set()

    def visit(node, depth=0):
        if not isinstance(node, dict) or depth > 60:
            return
        for k, v in node.get("c") or []:
            names.add(k)
            visit(v, depth + 1)
        for key in ("of", "cont"):
            if node.get(key):
                visit(node[key], depth + 1)

    for t in _types().values():
        visit(t)
    return frozenset(names)


def _looks_like_field(tok: str) -> bool:
    try:
        return tok in _all_field_names()
    except Exception:
        return False


def field_exists(name: str) -> bool:
    return available() and name in _all_field_names()
