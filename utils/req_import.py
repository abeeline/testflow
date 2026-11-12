"""批量导入需求清单（xlsx / csv）：表格一行就是一条需求。

研发的需求清单通常是两级的：上级需求（SR / Feature / 模块）下面挂若干条下级需求（AR / 子需求），
上级列往往是合并单元格。这里把每一行转成一条需求文本，并带出：
- req_id：用表格里的需求编号（如 AR-99165），后面的追溯矩阵直接用它，不再是 REQ-001 这种流水号；
- group：[上级, 本条]，用例导出时按它分成“一级模块 / 二级模块”。

列靠表头识别，识别不了的列原样拼进需求文本，不丢信息。
"""
import csv
import io
import re
from typing import Any, Dict, List, Optional

_ID_HEADERS = {"ar", "arid", "ar编号", "需求id", "需求编号", "reqid", "requirementid", "id", "编号", "子需求", "子需求id", "子需求编号"}
_PARENT_KEYS = ("sr", "上级", "父", "parent", "epic", "feature", "特性", "一级")
_NAME_KEYS = ("描述", "名称", "标题", "desc", "name", "title")
_DESC_KEYS = ("描述", "需求", "内容", "desc", "requirement", "text")
_DETAIL_KEYS = ("细化", "拆解", "分解", "说明", "备注", "detail", "note", "comment")
MAX_REQUIREMENTS = 500


def _norm(header: Any) -> str:
    return re.sub(r"[\s_\-/（）()：:]+", "", str(header or "")).lower()


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _one_line(text: str, limit: int = 0) -> str:
    text = re.sub(r"(?<=[^\x00-\x7f])\s*\n\s*|\s*\n\s*(?=[^\x00-\x7f])", "", str(text or "").strip())  # 中文单元格内换行不留空格
    text = " ".join(text.split())
    return text[:limit] if limit else text


def _short_title(text: str, limit: int = 40) -> str:
    first = re.split(r"[\n。；;]", str(text or "").strip(), maxsplit=1)[0]
    return _one_line(first, limit)


def _read_rows(filename: str, content: bytes) -> List[List[str]]:
    name = (filename or "").lower()
    if name.endswith((".csv", ".tsv", ".txt")):
        text = None
        for enc in ("utf-8-sig", "gb18030"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise ValueError("无法识别文件编码，请另存为 UTF-8 的 CSV")
        delimiter = "\t" if name.endswith(".tsv") or text.count("\t") > text.count(",") else ","
        return [[_cell(c) for c in row] for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    try:
        import openpyxl
        ws = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
        return [[_cell(c) for c in row] for row in ws.iter_rows(values_only=True)]
    except Exception as exc:
        raise ValueError(f"表格读取失败（支持 .xlsx / .csv）: {exc}") from exc


def _is_parent(header: str) -> bool:
    n = _norm(header)
    if n in _ID_HEADERS:
        return False
    return any(n.startswith(k) or (k not in ("sr",) and k in n) for k in _PARENT_KEYS)


def _detect_columns(headers: List[str]) -> Dict[str, Optional[int]]:
    cols: Dict[str, Optional[int]] = {"id": None, "parent_id": None, "parent_name": None, "desc": None, "detail": None}
    for i, h in enumerate(headers):
        n = _norm(h)
        if not n:
            continue
        if cols["id"] is None and n in _ID_HEADERS:
            cols["id"] = i
        elif _is_parent(h):
            key = "parent_name" if any(k in n for k in _NAME_KEYS) else "parent_id"
            if cols[key] is None:
                cols[key] = i
        elif cols["detail"] is None and any(k in n for k in _DETAIL_KEYS):
            cols["detail"] = i
        elif cols["desc"] is None and any(k in n for k in _DESC_KEYS):
            cols["desc"] = i
    return cols


def parse_requirement_sheet(filename: str, content: bytes) -> Dict[str, Any]:
    """返回 {"requirements": [文本], "meta": [{"req_id", "group"}], "groups": [...], "warnings": [...], "columns": {...}}。"""
    rows = [r for r in _read_rows(filename, content) if any(r)]
    if len(rows) < 2:
        raise ValueError("表格里没有数据行（第一行应是表头）")
    headers = rows[0]
    cols = _detect_columns(headers)
    if cols["desc"] is None and cols["detail"] is None:
        raise ValueError("没有找到需求描述列：表头里需要有“描述 / 需求 / 内容”之类的列名，当前表头：" + "、".join(h for h in headers if h))
    width = len(headers)
    id_label = _one_line(headers[cols["id"]]) if cols["id"] is not None else ""
    parent_label = _one_line(headers[cols["parent_id"]]) if cols["parent_id"] is not None else ""
    used = {k: v for k, v in cols.items() if v is not None}
    extra_cols = [i for i in range(width) if i not in used.values() and headers[i]]

    requirements: List[str] = []
    meta: List[Dict[str, Any]] = []
    warnings: List[str] = []
    seen_ids: Dict[str, int] = {}
    parent_id = parent_name = ""
    for line_no, raw in enumerate(rows[1:], start=2):
        row = list(raw) + [""] * (width - len(raw))

        def at(key: str) -> str:
            return row[cols[key]] if cols[key] is not None else ""

        # 上级列是合并单元格：只有第一行有值，往下沿用
        if at("parent_id") and at("parent_id") != parent_id:
            parent_id, parent_name = at("parent_id"), at("parent_name")
        elif at("parent_name"):
            parent_name = at("parent_name")
        desc, detail, rid = at("desc"), at("detail"), at("id")
        if not (desc or detail) or (cols["id"] is not None and not rid):
            continue
        if len(requirements) >= MAX_REQUIREMENTS:
            warnings.append(f"需求超过 {MAX_REQUIREMENTS} 条，后面的行没有导入")
            break

        prefix = id_label if re.fullmatch(r"[A-Za-z]{1,6}", id_label) else "REQ"
        if not rid:
            req_id = f"REQ-{len(requirements) + 1:03d}"
        elif re.fullmatch(r"[\d.]+", rid):
            req_id = f"{prefix.upper()}-{rid}"
        else:
            req_id = _one_line(rid)
        if req_id in seen_ids:
            parent_tag = re.sub(r"\W+", "", f"{parent_label}{parent_id}")
            candidate = f"{req_id}-{parent_tag}" if parent_tag and f"{req_id}-{parent_tag}" not in seen_ids else ""
            n = 2
            while not candidate or candidate in seen_ids:
                candidate, n = f"{req_id}-{n}", n + 1
            warnings.append(f"第 {line_no} 行的需求编号 {rid} 与第 {seen_ids[req_id]} 行重复，本次按 {candidate} 处理，请核对原表")
            req_id = candidate
        seen_ids[req_id] = line_no

        head = [f"{id_label or '需求'} {rid}".strip() if rid else req_id]
        if parent_id or parent_name:
            head.append(" ".join(x for x in (parent_label, parent_id, _one_line(parent_name)) if x))
        head += [f"{_one_line(headers[i])} {_one_line(row[i])}" for i in extra_cols if row[i] and len(row[i]) <= 40]
        body = []
        if desc:
            body.append(f"{_one_line(headers[cols['desc']])}：{desc}")
        if detail:
            body.append(f"{_one_line(headers[cols['detail']])}：\n{detail}")
        body += [f"{_one_line(headers[i])}：{row[i]}" for i in extra_cols if len(row[i]) > 40]
        requirements.append("【" + "｜".join(head) + "】\n" + "\n".join(body))

        level2 = " ".join(x for x in (f"{id_label} {rid}".strip() if rid else req_id, _short_title(desc or detail)) if x)
        level1 = " ".join(x for x in (parent_label, parent_id, _one_line(parent_name, 60)) if x)
        meta.append({"req_id": req_id, "group": [level1, level2] if level1 else [level2]})

    if not requirements:
        raise ValueError("没有读到需求：需求编号列或描述列为空")
    groups: Dict[str, int] = {}
    for m in meta:
        if len(m["group"]) == 2:
            groups[m["group"][0]] = groups.get(m["group"][0], 0) + 1
    return {
        "requirements": requirements,
        "meta": meta,
        "groups": [{"name": k, "count": v} for k, v in groups.items()],
        "warnings": warnings,
        "columns": {k: _one_line(headers[v]) for k, v in used.items()},
    }
