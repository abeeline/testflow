"""规范核对插件：需求澄清阶段按规范逐条核对需求，每份规范一个核对器。

内置的是 TS 38.331（RRC ASN.1 IE 树，见 core/clarification.py）。其它规范（例如 TS 24.501 NAS、TS 38.321 MAC）
这里不带数据，也不让模型凭记忆补：由用户把规范里的取值表整理成 JSON / CSV 放到 config/spec_tables/
（或环境变量 TESTFLOW_SPEC_TABLES 指定的目录），加载后按表核对需求写明的取值。没加载的规范，澄清页会写明
“未核对”，不会假装核对过。

表格式（JSON）：
    {"spec": "TS 24.501", "version": "V18.6.0",
     "entries": [{"name": "5GMM cause", "values": ["#3", "#6", "#7"], "note": "Table 9.11.3.2.1"},
                 {"name": "T3512", "range": [0, 31], "unit": "min"}]}
CSV：表头 spec,version,name,values,min,max,unit,note；values 用 | 分隔。
"""
import csv
import io
import json
import os
import re
from typing import Any, Callable, Dict, Iterable, List, Optional

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "spec_tables")

# name -> {"name", "spec", "kind", "builtin", "fn", "entries"}
_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register(name: str, spec: str, fn: Optional[Callable] = None, *, kind: str = "spec", builtin: bool = False,
             description: str = "", entries: int = 0) -> None:
    """fn(builder, reqs, texts_by_req) 往澄清单里加条目；builtin 的核对器（38.331）由 build_clarifications 直接调用。"""
    _REGISTRY[name] = {"name": name, "spec": spec, "kind": kind, "builtin": builtin, "fn": fn,
                       "description": description, "entries": entries}


def unregister(name: str) -> None:
    _REGISTRY.pop(name, None)


def checkers(kind: Optional[str] = None) -> List[Dict[str, Any]]:
    return [c for c in _REGISTRY.values() if kind is None or c["kind"] == kind]


def coverage() -> List[Dict[str, Any]]:
    """给前端看：哪些规范核对了、哪些没有数据。"""
    out = [{k: c[k] for k in ("name", "spec", "kind", "builtin", "description", "entries")} for c in _REGISTRY.values()]
    loaded = {c["spec"] for c in _REGISTRY.values() if c["kind"] == "spec"}
    for spec in ("TS 24.501", "TS 38.321"):
        if not any(spec in s for s in loaded):
            out.append({"name": "", "spec": spec, "kind": "spec", "builtin": False, "entries": 0,
                        "description": "未加载规范表，不核对（可把取值表放到 config/spec_tables/）"})
    return out


def run(builder: Any, reqs: List[Dict[str, Any]], texts_by_req: Dict[str, List[str]]) -> None:
    for c in list(_REGISTRY.values()):
        if c["builtin"] or not c["fn"]:
            continue
        c["fn"](builder, reqs, texts_by_req)


# ---------- 用户提供的规范表 ----------


def _norm(v: Any) -> str:
    return re.sub(r"\s+", "", str(v or "")).lower()


def _as_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else [v]


def parse_table(text: str, filename: str = "") -> Dict[str, Any]:
    """JSON 或 CSV 文本 → {"spec", "version", "entries"}。"""
    text = text.lstrip("﻿")
    if filename.lower().endswith(".json") or text.lstrip().startswith("{"):
        data = json.loads(text)
        entries = [e for e in data.get("entries") or [] if isinstance(e, dict) and e.get("name")]
        return {"spec": str(data.get("spec") or "").strip(), "version": str(data.get("version") or ""), "entries": entries}
    rows = list(csv.DictReader(io.StringIO(text)))
    spec = next((r.get("spec") for r in rows if r.get("spec")), "") or ""
    version = next((r.get("version") for r in rows if r.get("version")), "") or ""
    entries = []
    for r in rows:
        if not (r.get("name") or "").strip():
            continue
        e: Dict[str, Any] = {"name": r["name"].strip()}
        if (r.get("values") or "").strip():
            e["values"] = [v.strip() for v in r["values"].split("|") if v.strip()]
        if (r.get("min") or "").strip() and (r.get("max") or "").strip():
            e["range"] = [float(r["min"]), float(r["max"])]
        for k in ("unit", "note"):
            if (r.get(k) or "").strip():
                e[k] = r[k].strip()
        entries.append(e)
    return {"spec": spec.strip(), "version": version, "entries": entries}


def _value_ok(entry: Dict[str, Any], value: Any) -> Optional[str]:
    """不合规返回原因，合规 / 不能判断返回 None。"""
    for v in _as_list(value):
        s = str(v).strip()
        if not s:
            continue
        if entry.get("values"):
            allowed = {_norm(x) for x in entry["values"]}
            if _norm(s) not in allowed and _norm(re.sub(r"^#", "", s)) not in {a.lstrip("#") for a in allowed}:
                return f"{s} 不在规范表取值里（{'、'.join(map(str, entry['values'][:12]))}）"
        if entry.get("range"):
            m = re.fullmatch(r"[-+]?\d+(?:\.\d+)?", re.sub(r"\s*" + re.escape(str(entry.get("unit") or "")) + r"$", "", s)
                             if entry.get("unit") else s)
            if not m:
                return f"{s} 不是数值，规范表给的是 {entry['range'][0]}..{entry['range'][1]} {entry.get('unit', '')}".strip()
            lo, hi = entry["range"]
            if not lo <= float(m.group(0)) <= hi:
                return f"{s} 超出规范表范围 {lo}..{hi} {entry.get('unit', '')}".strip()
    return None


def table_checker(table: Dict[str, Any]) -> Callable:
    by_name = {_norm(e["name"]): e for e in table["entries"]}
    spec = table["spec"] or "用户规范表"
    label = f"{spec} {table.get('version') or ''}".strip()

    def check(b: Any, reqs: List[Dict[str, Any]], texts_by_req: Dict[str, List[str]]) -> None:
        for req in reqs:
            rid = str(req.get("req_id"))
            seen = set()
            pairs = [(c.get("name"), c.get("value"), c.get("source_text") or "") for c in req.get("explicit_configs") or []
                     if isinstance(c, dict)]
            for t in texts_by_req.get(rid, []):
                for e in table["entries"]:
                    for m in re.finditer(re.escape(e["name"]) + r"\s*(?:=|为|设为|取值为|配置为)\s*([^\s，,。；;）)]+)", t):
                        pairs.append((e["name"], m.group(1), t))
            for name, value, src in pairs:
                e = by_name.get(_norm(name))
                if not e or (e["name"], str(value)) in seen:
                    continue
                seen.add((e["name"], str(value)))
                why = _value_ok(e, value)
                if why:
                    b.add(rid, "value_type", f"{e['name']} = {value}：{why}；请按 {spec} 给出取值", blocking=True,
                          evidence=f"{label}（用户提供的规范表）：{e['name']} {e.get('note') or ''}".strip(),
                          raised_by=f"{spec} 核对", source_text=str(src), field=e["name"])

    return check


def load_tables(directory: Optional[str] = None) -> List[str]:
    """读目录里的规范表并注册核对器，返回加载的规范名。目录不存在就什么都不做。"""
    d = directory or os.environ.get("TESTFLOW_SPEC_TABLES") or _DEFAULT_DIR
    for name in [n for n, c in _REGISTRY.items() if c.get("from_table")]:
        unregister(name)
    loaded: List[str] = []
    if not os.path.isdir(d):
        return loaded
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith((".json", ".csv")):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                table = parse_table(f.read(), fn)
        except Exception:
            continue
        if not table["entries"]:
            continue
        name = f"table:{fn}"
        register(name, table["spec"] or fn, table_checker(table), entries=len(table["entries"]),
                 description=f"用户提供的规范表 {fn}（{len(table['entries'])} 项）")
        _REGISTRY[name]["from_table"] = True
        loaded.append(table["spec"] or fn)
    return loaded


def register_table(table: Dict[str, Any], name: str) -> None:
    register(f"table:{name}", table.get("spec") or name, table_checker(table), entries=len(table.get("entries") or []),
             description=f"用户提供的规范表 {name}（{len(table.get('entries') or [])} 项）")
    _REGISTRY[f"table:{name}"]["from_table"] = True


def texts_for(reqs: Iterable[Dict[str, Any]], text_fn: Callable[[Dict[str, Any]], List[str]]) -> Dict[str, List[str]]:
    return {str(r.get("req_id")): text_fn(r) for r in reqs}


register("38.331", "TS 38.331", None, builtin=True,
         description="RRC ASN.1 IE 树：字段是否存在、位置、取值类型")
load_tables()
