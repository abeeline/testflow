"""把 TS 38.331 的 ASN.1 编译结果转成 TestFlow 用的 IE 树（core/asn1/nr_rrc_asn1_tree.json.gz）。

输入是 pycrate 的 ASN.1 编译器（pycrate_asn1c）为 NR RRC 生成的 Python 模块（RRCNR.py）。
本脚本只用 ast 静态读取这个文件，不 import、不执行其中的代码。

用法：
    python scripts/build_rrc_asn1_tree.py <RRCNR.py> --version "TS 38.331 v18.2.0" [--out core/asn1/nr_rrc_asn1_tree.json.gz]

想换成别的规范版本（例如严格的 v18.2.0）：
    1. 从 3GPP 下载对应版本的 38.331（38331-i20.zip），按规范附带的方法抽出 ASN.1 文本（-- ASN1START ... -- ASN1STOP 之间）；
    2. 在装有 pycrate 的机器上用它的编译器把 ASN.1 编成 Python 模块：
       python -m pycrate_asn1c.asnproc 或 pycrate 自带的 tools/pycrate_asn1compile.py -i <asn 目录> -o RRCNR
    3. 用本脚本转成 IE 树，替换 core/asn1/nr_rrc_asn1_tree.json.gz，--version 写清版本。

输出格式（紧凑 JSON）：
    {"meta": {...}, "types": {类型名: 节点}}
    节点：{"t": 种类, "ref": 引用的类型名, "c": [[子字段名, 子节点], ...], "opt": 1, "def": 默认值,
           "e": [枚举值], "x": 1(可扩展), "rng": [下限, 上限], "sz": [下限, 上限], "of": 成员节点, "cont": 内含节点}
    种类沿用 pycrate：SEQ / SET / CHOICE / SEQ_OF / SET_OF / ENUM / INT / BOOL / NULL / BIT_STR / OCT_STR / 各类字符串。
"""
import argparse
import ast
import gzip
import json
import os
import sys
from typing import Any, Dict, List, Optional

_CTORS = {"SEQ", "SET", "CHOICE", "SEQ_OF", "SET_OF", "ENUM", "INT", "BOOL", "NULL", "BIT_STR", "OCT_STR",
          "REAL", "OID", "REL_OID", "STR_UTF8", "STR_IA5", "STR_VIS", "STR_PRINT", "STR_NUM", "STR_BMP",
          "STR_UNIV", "STR_TELE", "STR_GRAPH", "STR_GENE", "TIME_UTC", "TIME_GEN", "OPEN", "ANY", "EXT", "EMB_PDV",
          "CHAR_STR"}


def _lit(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def _range(call: ast.AST) -> Optional[List[Any]]:
    """ASN1Set(rv=[...], rr=[ASN1RangeInt(lb=, ub=)]) → [下限, 上限]（只取根部分）。"""
    if not isinstance(call, ast.Call):
        return None
    kw = {k.arg: k.value for k in call.keywords}
    lows: List[Any] = []
    highs: List[Any] = []
    rv = _lit(kw.get("rv")) if kw.get("rv") is not None else None
    for v in rv or []:
        if isinstance(v, (int, float)):
            lows.append(v)
            highs.append(v)
    rr = kw.get("rr")
    if isinstance(rr, ast.List):
        for item in rr.elts:
            if isinstance(item, ast.Call):
                ikw = {k.arg: _lit(k.value) for k in item.keywords}
                if ikw.get("lb") is not None:
                    lows.append(ikw["lb"])
                if ikw.get("ub") is not None:
                    highs.append(ikw["ub"])
    if not lows and not highs:
        return None
    return [min(lows) if lows else None, max(highs) if highs else None]


class _Module:
    def __init__(self, name: str):
        self.name = name
        self.objs: Dict[str, Dict[str, Any]] = {}

    def feed(self, stmt: ast.Assign):
        if len(stmt.targets) != 1:
            return
        tgt, val = stmt.targets[0], stmt.value
        if isinstance(tgt, ast.Name) and isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
                and val.func.id in _CTORS:
            kw = {k.arg: k.value for k in val.keywords}
            obj: Dict[str, Any] = {"t": val.func.id, "name": _lit(kw.get("name")) if kw.get("name") else None}
            ref = kw.get("typeref")
            if isinstance(ref, ast.Call) and ref.args:
                pair = _lit(ref.args[0])
                if isinstance(pair, tuple) and len(pair) == 2:
                    obj["ref"] = pair[1]
            if kw.get("opt") is not None and _lit(kw["opt"]):
                obj["opt"] = 1
            if "default" in kw:
                obj["opt"] = 1
                d = _lit(kw["default"])
                if isinstance(d, (str, int, float, bool)):
                    obj["def"] = d
            self.objs[tgt.id] = obj
            return
        if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id in self.objs:
            obj = self.objs[tgt.value.id]
            attr = tgt.attr
            if attr == "_cont":
                if isinstance(val, ast.Name):
                    obj["of_var"] = val.id
                elif isinstance(val, ast.Call) and val.args and isinstance(val.args[0], ast.List):
                    items = []
                    for el in val.args[0].elts:
                        if isinstance(el, ast.Tuple) and len(el.elts) == 2:
                            k = _lit(el.elts[0])
                            v = el.elts[1]
                            items.append((k, v.id if isinstance(v, ast.Name) else _lit(v)))
                    obj["items"] = items
            elif attr == "_ext":
                obj["ext"] = val is not None and not (isinstance(val, ast.Constant) and val.value is None)
            elif attr == "_const_val":
                r = _range(val)
                if r:
                    obj["rng"] = r
            elif attr == "_const_sz":
                r = _range(val)
                if r:
                    obj["sz"] = r
            elif attr == "_const_cont" and isinstance(val, ast.Name):
                obj["cont_var"] = val.id


def _serialize(mod: _Module, var: str, top_names: Dict[str, str], depth: int = 0) -> Dict[str, Any]:
    obj = mod.objs[var]
    out: Dict[str, Any] = {"t": obj["t"]}
    for k in ("ref", "opt", "def", "rng", "sz"):
        if k in obj:
            out[k] = obj[k]
    if obj.get("ext"):
        out["x"] = 1
    items = obj.get("items")
    if items is not None:
        if obj["t"] == "ENUM":
            out["e"] = [k for k, _ in items]
        elif obj["t"] in ("SEQ", "SET", "CHOICE"):
            out["c"] = [[k, _serialize(mod, v, top_names, depth + 1)] for k, v in items
                        if isinstance(v, str) and v in mod.objs]
        elif obj["t"] == "BIT_STR":
            out["named"] = [k for k, _ in items]
    if obj.get("of_var") in mod.objs:
        out["of"] = _serialize(mod, obj["of_var"], top_names, depth + 1)
    if obj.get("cont_var") in mod.objs:
        out["cont"] = _serialize(mod, obj["cont_var"], top_names, depth + 1)
    # 只是引用别的类型、自己没有内容时，靠 ref 解析；有内容（如 SetupRelease 实例化）时以自己的内容为准
    if "ref" in out and any(k in out for k in ("c", "e", "of", "cont")):
        out["inline"] = 1
    return out


def build(path: str, version: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    types: Dict[str, Any] = {}
    modules = []
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        mod = _Module(cls.name)
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign):
                mod.feed(stmt)
        modules.append(mod)
    for mod in sorted(modules, key=lambda m: m.name != "NR_RRC_Definitions"):
        top = {var: o["name"] for var, o in mod.objs.items() if not var.startswith("_") and o.get("name")}
        for var, name in top.items():
            if name in types:
                continue
            types[name] = _serialize(mod, var, top)
    return {
        "meta": {
            "spec": "TS 38.331",
            "version": version,
            "source": os.path.basename(path),
            "generator": "scripts/build_rrc_asn1_tree.py",
            "type_count": len(types),
        },
        "types": types,
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("module", help="pycrate 编译出的 RRCNR.py")
    ap.add_argument("--version", required=True, help="规范版本说明，例如 'TS 38.331 v18.2.0'")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "core", "asn1",
                                                  "nr_rrc_asn1_tree.json.gz"))
    args = ap.parse_args(argv)
    data = build(args.module, args.version)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(args.out, "wb", mtime=0) as f:
        f.write(raw)
    print(f"{data['meta']['type_count']} 个类型 → {args.out}（{len(raw) // 1024} KB 未压缩）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
