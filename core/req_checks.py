"""需求澄清的第 3、4、5 层：需求自身的一致性、歧义、复述确认。

第 1、2 层（字段是否存在、位置/取值是否合规）按规范核对，见 core/clarification.py 和 core/spec_checkers.py。
这里查的是规范查不出来、但会让后面设计跑偏的问题：

    release_mismatch     需求标 R17，却引用了 -r18 / -v18xx 字段
    text_config_conflict 需求正文写的取值和 explicit_configs 不一致（阻塞：不知道该信哪个）
    inconsistent_value   同一 SR 下同一参数在不同需求里取值不同（提示确认是有意的不同场景）
    duplicate            两条需求的标题+描述几乎相同
    ambiguity            期望/判据里有“及时、适当、左右”这类没法判定的词（判据里的阻塞），或模型给出了多种读法

复述卡片（restatement_cards）把每条需求按“前提 / 触发 / 期望 / 配置 / 判据”复述一遍，需求方逐条确认“我的理解对不对”，
全部确认后才能定稿。
"""
import difflib
import re
from typing import Any, Dict, List

from core import spec_checkers

_REL_REQ = re.compile(r"(?:Release|Rel|R)[\s\-：:]*?(1[5-9])\b", re.I)
_REL_FIELD = re.compile(r"(?<![A-Za-z0-9])([a-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*-(?:r(1[5-9])|v(1[5-9])\d{2}))(?![A-Za-z0-9\-])")
# “正常注册 / RRC 建立正常完成”是测试里约定俗成的判据（流程走完、无异常），不当成含糊词
_VAGUE = re.compile(r"适当|合理|尽快|(?<!以)及时|快速|稳定(?!性)|大约|左右|若干|一定时间|较短|较长|较快|较慢|明显|尽量|必要时|等等|TBD|待定|"
                    r"一段时间|短时间|很快|很短|少量|大量")
_SET_VALUE = r"\s*(?:=|为|设为|设置为|配置为|取值为)\s*([^\s，,。；;）)、]+)"


def _join(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)] if v not in (None, "") else []


def req_release(req: Dict[str, Any]) -> int:
    src = req.get("source") or {}
    for t in _join(req.get("constraints")) + [str(src.get("section") or "") if isinstance(src, dict) else "",
                                               str(req.get("feature") or ""), str(req.get("release") or "")]:
        m = _REL_REQ.search(t)
        if m:
            return int(m.group(1))
    return 0


def _body_texts(req: Dict[str, Any]) -> List[str]:
    """需求正文（不含原文引用 source_text：那是证据，不是需求的结论）。"""
    out = _join(req.get("title")) + _join(req.get("description"))
    for k in ("preconditions", "trigger", "expected", "constraints"):
        out += _join(req.get(k))
    out += _join((req.get("acceptance") or {}).get("pass_fail"))
    return out


def _vals(v: Any) -> List[str]:
    return [re.sub(r"\s+", "", str(x)) for x in (v if isinstance(v, list) else [v]) if str(x).strip()]


def check_consistency(b: Any, reqs: List[Dict[str, Any]], texts_by_req: Dict[str, List[str]]) -> None:
    by_group: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for req in reqs:
        rid = str(req.get("req_id"))
        body = _body_texts(req)
        # 版本不一致
        rel = req_release(req)
        if rel:
            seen = set()
            for t in body + [f"{c.get('name', '')}" for c in req.get("explicit_configs") or [] if isinstance(c, dict)]:
                for m in _REL_FIELD.finditer(t):
                    f = m.group(1)
                    frel = int(m.group(2) or m.group(3))
                    if frel > rel and f not in seen:
                        seen.add(f)
                        b.add(rid, "release_mismatch",
                              f"需求标为 R{rel}，却引用了 R{frel} 引入的字段 {f}；确认需求版本，或说明这是在 R{rel} 下验证该字段不出现",
                              blocking=False, evidence=f"字段后缀 {f.rsplit('-', 1)[1]} 表示 Rel-{frel} 引入",
                              raised_by="一致性检查", source_text=t, field=f)
        # 正文取值和显式配置不一致
        for c in req.get("explicit_configs") or []:
            if not isinstance(c, dict) or not c.get("name"):
                continue
            want = set(_vals(c.get("value")))
            if not want:
                continue
            for t in body:
                for m in re.finditer(re.escape(str(c["name"])) + _SET_VALUE, t):
                    got = re.sub(r"\s+", "", m.group(1))
                    if got not in want and not any(got in w or w in got for w in want):
                        b.add(rid, "text_config_conflict",
                              f"需求正文写 {c['name']} = {got}，显式配置是 {'、'.join(sorted(want))}；请确认以哪个为准",
                              blocking=True, evidence=f"正文：{t[:120]}；配置原文：{str(c.get('source_text') or '')[:120]}",
                              raised_by="一致性检查", source_text=t, field=str(c["name"]))
            grp = str((req.get("group") or [""])[0] or "")
            if grp and len(want) == 1:
                by_group.setdefault(grp, {}).setdefault(str(c["name"]), {}).setdefault(next(iter(want)), []).append(rid)
    for grp, names in by_group.items():
        for name, values in names.items():
            if len(values) < 2:
                continue
            first = sorted(values.items(), key=lambda kv: kv[1][0])
            listing = "；".join(f"{v}（{'、'.join(r[:4])}）" for v, r in first[:5])
            b.add(first[0][1][0], "inconsistent_value",
                  f"{grp} 下 {name} 在不同需求里取值不同：{listing}；确认是有意的不同场景，不是笔误",
                  blocking=False, evidence="同一 SR 下的需求取值对比", raised_by="一致性检查", field=name)
    # 重复需求
    norm = [(str(r.get("req_id")), re.sub(r"\s+", "", f"{r.get('title', '')}|{r.get('description', '')}")) for r in reqs]
    for i, (ra, ta) in enumerate(norm):
        if len(ta) < 12:
            continue
        for rb, tb in norm[i + 1:]:
            if ta == tb or (abs(len(ta) - len(tb)) < 0.2 * len(ta) and difflib.SequenceMatcher(None, ta, tb).ratio() >= 0.92):
                b.add(rb, "duplicate", f"{rb} 与 {ra} 的标题和描述几乎相同；确认是否重复，或补充两者的区别",
                      blocking=False, evidence=f"{ra}：{ta[:80]}", raised_by="一致性检查")


def check_ambiguity(b: Any, reqs: List[Dict[str, Any]], texts_by_req: Dict[str, List[str]]) -> None:
    for req in reqs:
        rid = str(req.get("req_id"))
        fields = [("判据", t, True) for t in _join((req.get("acceptance") or {}).get("pass_fail"))]
        fields += [("期望", t, False) for t in _join(req.get("expected"))]
        fields += [("触发", t, False) for t in _join(req.get("trigger"))]
        hits = 0
        for where, t, blocking in fields:
            words = list(dict.fromkeys(_VAGUE.findall(t)))
            if not words or hits >= 4:
                continue
            hits += 1
            b.add(rid, "ambiguity", f"{where}里的“{'、'.join(words)}”没有可判定的标准：{t[:120]}；请给出具体数值或判据",
                  blocking=blocking, evidence="不能判定通过/失败的措辞" if blocking else "措辞含糊，设计会按惯例取值",
                  raised_by="歧义检查", source_text=t)
    for amb in getattr(b, "ambiguities", None) or []:
        if not isinstance(amb, dict) or not amb.get("req_id"):
            continue
        readings = [str(x) for x in amb.get("readings") or [] if str(x).strip()]
        if len(readings) < 2:
            continue
        q = amb.get("question") or f"“{str(amb.get('text') or '')[:60]}”有多种读法，请确认按哪种设计"
        b.add(str(amb["req_id"]), "ambiguity", f"{q}：" + "；".join(f"读法{i + 1}：{r}" for i, r in enumerate(readings[:4])),
              blocking=True, evidence="综合评审给出的多种读法", raised_by="综合评审", source_text=str(amb.get("text") or ""))


def restatement(req: Dict[str, Any]) -> Dict[str, Any]:
    """把需求按固定结构复述一遍：需求方看的是“AI 理解成了什么”，不是 AI 改写后的漂亮文字。"""
    cfgs = []
    for c in req.get("explicit_configs") or []:
        if isinstance(c, dict) and c.get("name"):
            v = c.get("value")
            cfgs.append(f"{c['name']} = {' / '.join(map(str, v)) if isinstance(v, list) else v}")
    parts = {
        "前提": _join(req.get("preconditions")),
        "触发": _join(req.get("trigger")),
        "期望": _join(req.get("expected")),
        "配置": cfgs,
        "判据": _join((req.get("acceptance") or {}).get("pass_fail")),
    }
    rel = req_release(req)
    text = (f"{'在 ' + '；'.join(parts['前提']) + ' 的前提下，' if parts['前提'] else ''}"
            f"{'当 ' + '；'.join(parts['触发']) + ' 时，' if parts['触发'] else ''}"
            f"{'应当 ' + '；'.join(parts['期望']) + '。' if parts['期望'] else '（需求没有写期望行为）'}"
            f"{' 判定通过的标准：' + '；'.join(parts['判据']) + '。' if parts['判据'] else ' （需求没有写判据）'}")
    gaps = [k for k in ("触发", "期望", "判据") if not parts[k]]
    return {"req_id": str(req.get("req_id")), "title": str(req.get("title") or ""), "release": f"R{rel}" if rel else "",
            "parts": parts, "text": text, "gaps": gaps}


def restatement_cards(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    und = (spec or {}).get("understanding") or {}
    items = ((spec or {}).get("clarifications") or {}).get("items") or []
    cards = []
    for req in (spec or {}).get("final_requirements") or []:
        if not isinstance(req, dict) or not req.get("req_id"):
            continue
        card = restatement(req)
        mine = [it for it in items if it.get("req_id") == card["req_id"]]
        card["open_items"] = [it["id"] for it in mine if it.get("status") == "open"]
        card["blocking_open"] = [it["id"] for it in mine if it.get("status") == "open" and it.get("blocking")]
        card["confirmed"] = bool((und.get(card["req_id"]) or {}).get("confirmed"))
        card["confirmed_by"] = (und.get(card["req_id"]) or {}).get("by") or ""
        card["note"] = (und.get(card["req_id"]) or {}).get("note") or ""
        cards.append(card)
    return cards


spec_checkers.register("consistency", "需求一致性", check_consistency, kind="consistency",
                       description="版本、正文与配置、同组取值、重复需求")
spec_checkers.register("ambiguity", "需求歧义", check_ambiguity, kind="ambiguity",
                       description="判据/期望里的含糊措辞，综合评审给出的多种读法")
