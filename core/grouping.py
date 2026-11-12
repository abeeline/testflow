"""用例分组：把用例按“一级模块 / 二级模块”归到套件里，导出和界面都按这棵树展示。

分组来自需求：
- 需求带 group（批量导入需求表时由表格的上级列给出，或由需求解析写出），就用它；
- 否则一级取 feature，二级取“需求编号 + 标题”。
一条用例跟随它追溯到的第一条需求。
"""
from typing import Any, Dict, Iterable, List

UNGROUPED = "未分组"
_DEFAULT_FEATURES = {"", "MODEM_SYSTEM"}


def _clean(value: Any, limit: int = 80) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def requirement_group(req: Dict[str, Any]) -> List[str]:
    """返回 [一级, 二级]。"""
    req = req if isinstance(req, dict) else {}
    raw = req.get("group")
    levels = [_clean(x) for x in raw if _clean(x)] if isinstance(raw, list) else ([_clean(raw)] if _clean(raw) else [])
    rid, title = _clean(req.get("req_id")), _clean(req.get("title"), 60)
    own = " ".join(x for x in (rid, title) if x) or UNGROUPED
    if len(levels) >= 2:
        return levels[:2]
    if len(levels) == 1:
        return [levels[0], own]
    feature = _clean(req.get("feature"))
    return [UNGROUPED if feature in _DEFAULT_FEATURES else feature, own]


def suite_of(tc: Dict[str, Any], req_index: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """用例所属套件：{"level1", "level2"}。"""
    for rid in (tc.get("trace") or {}).get("req_ids") or []:
        req = req_index.get(str(rid))
        if req:
            l1, l2 = requirement_group(req)
            return {"level1": l1, "level2": l2}
    return {"level1": UNGROUPED, "level2": UNGROUPED}


def ensure_suite(tc: Dict[str, Any], req_index: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """用例上已有 suite 就用它（旧记录没有时现算）。"""
    suite = tc.get("suite") if isinstance(tc, dict) else None
    if isinstance(suite, dict) and suite.get("level1"):
        return {"level1": str(suite["level1"]), "level2": str(suite.get("level2") or UNGROUPED)}
    return suite_of(tc or {}, req_index)


def attach_suites(tcs: Iterable[Dict[str, Any]], req_index: Dict[str, Dict[str, Any]]) -> None:
    for tc in tcs or []:
        if isinstance(tc, dict):
            tc["suite"] = suite_of(tc, req_index)


def suite_tree(entries: Iterable[Dict[str, Any]], id_key: str = "case_id") -> List[Dict[str, Any]]:
    """把带 suite 的条目汇成两级树，保持首次出现的顺序。

    返回 [{"name", "count", "children": [{"name", "count", "case_ids": [...]}]}]
    """
    tree: Dict[str, Dict[str, List[str]]] = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        suite = e.get("suite") or {}
        l1 = str(suite.get("level1") or UNGROUPED)
        l2 = str(suite.get("level2") or UNGROUPED)
        tree.setdefault(l1, {}).setdefault(l2, []).append(str(e.get(id_key) or ""))
    return [{"name": l1, "count": sum(len(v) for v in subs.values()),
             "children": [{"name": l2, "count": len(ids), "case_ids": ids} for l2, ids in subs.items()]}
            for l1, subs in tree.items()]


def restore_groups(requirements: List[Dict[str, Any]], originals: List[Dict[str, Any]]) -> int:
    """模型改写需求时丢了 group 的，按 req_id 从改写前的需求补回。返回补回的条数。"""
    by_id = {str(r.get("req_id")): r.get("group") for r in originals or [] if isinstance(r, dict) and r.get("group")}
    n = 0
    for r in requirements or []:
        if isinstance(r, dict) and not r.get("group") and by_id.get(str(r.get("req_id"))):
            r["group"] = list(by_id[str(r.get("req_id"))])
            n += 1
    return n
