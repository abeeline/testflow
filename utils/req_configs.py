"""需求里写明的协议配置：从原文摘出配置行，并检查最终基站/仪表 case 是否保留了这些取值。

两层保障：
1) LLM 在需求解析时把显式配置写进 requirement.explicit_configs（name/value/source_text），
   综合评审丢掉时按 req_id 补回；
2) 规则从需求原文按行摘出“像配置”的句子（参数=值、带单位的数值、频段、定时器、ASN.1 字段名），
   原样放进 Amarisoft / 协议 bundle，并检查其中的取值是否出现在生成的 case 里。
"""
import json
import re
from typing import Any, Dict, Iterable, List

_MAX_LINES = 80
_MAX_LINE_LEN = 300

_UNIT = r"(?:dBm|dB|MHz|kHz|KHz|GHz|Hz|ms|min|s|PRB|RB|Mbps|kbps|%)"
_VALUE_PATTERNS = [
    re.compile(r"-?\d+(?:\.\d+)?\s*" + _UNIT + r"(?![A-Za-z])"),          # 带单位数值：-110dBm、100 MHz、12min
    re.compile(r"\b[nN]\d{1,3}\b|\b[Bb]and\s*\d{1,3}\b|\bB\d{1,3}\b"),     # 频段：n78、Band 3、B41
    re.compile(r"\bT3\d{2,3}\b|\bN3\d{2}\b"),                                # 定时器/计数器：T3412、T310、N310
    re.compile(r"\b[A-Za-z][\w\-]*-r1[5-9]\b"),                              # ASN.1 字段：xxx-r16
    re.compile(r"\b(?:ms|sf|s|min|dB|n)\d+\b"),                              # 枚举取值：ms1000、sf20、dB3
]
_KEYWORDS = re.compile(
    r"ARFCN|EARFCN|SSB|SCS|PCI|PLMN|MCC|MNC|TAC|APN|DNN|S-NSSAI|SNSSAI|eDRX|PSM|DRX|PRACH|BWP|TDD|FDD|"
    r"RSRP|RSRQ|SINR|q-RxLevMin|qRxLevMin|hysteresis|timeToTrigger|threshold|offset|cause|reject|"
    r"sib\d*|SIB\d*|MIB|measConfig|reportConfig|RRC|NAS|5GMM|EMM|bandwidth|带宽|子载波|频点|频段|门限|定时器|功率|拒绝原因",
    re.IGNORECASE,
)
_ASSIGN = re.compile(r"([A-Za-z][\w\-.\[\]/]*)\s*(?:=|:|：|设为|设置为|配置为|取值为?)\s*([^\s,，；;。]+)")


def _segments(text: str) -> Iterable[str]:
    for line in re.split(r"[\r\n]+", text or ""):
        line = line.strip(" \t-*•·")
        if not line:
            continue
        if len(line) <= _MAX_LINE_LEN:
            yield line
            continue
        for part in re.split(r"(?<=[；;。])", line):
            part = part.strip()
            if part:
                yield part[:_MAX_LINE_LEN]


def value_tokens(text: str) -> List[str]:
    """一句配置里可校验的取值片段（去重、保序）。"""
    tokens: List[str] = []
    for m in _ASSIGN.finditer(text or ""):
        tokens.append(m.group(2))
    for pat in _VALUE_PATTERNS:
        tokens.extend(m.group(0) for m in pat.finditer(text or ""))
    seen, out = set(), []
    for t in tokens:
        t = t.strip().strip("\"'“”（）()")
        n = _norm(t)
        if len(n) < 2 or n in seen:
            continue
        seen.add(n)
        out.append(t)
    return out


def extract_config_lines(requirement_input: List[str]) -> List[Dict[str, Any]]:
    """从需求原文按行摘出配置类句子，原样保留。"""
    out: List[Dict[str, Any]] = []
    seen = set()
    for text in requirement_input or []:
        for seg in _segments(str(text or "")):
            if seg in seen:
                continue
            tokens = value_tokens(seg)
            has_assign = bool(_ASSIGN.search(seg))
            if not tokens or not (has_assign or _KEYWORDS.search(seg)):
                continue
            seen.add(seg)
            out.append({"line_id": f"SRC-{len(out) + 1:02d}", "text": seg, "values": tokens})
            if len(out) >= _MAX_LINES:
                return out
    return out


def _norm(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return re.sub(r"[\s\"'“”]", "", str(value if value is not None else "")).lower()


def blob_of(item: Dict[str, Any], keys: Iterable[str]) -> str:
    return _norm({k: item.get(k) for k in keys if k in item})


def value_present(value: Any, blob: str) -> bool:
    """取值是否出现在 case 的配置字段里（忽略空白和大小写）。
    带单位的取值（如 100MHz）在 case 里常写成 bandwidth_mhz: 100，所以再按“独立的数字”找一次；
    数字前后不能紧挨字母或数字，避免 100 命中 ms1000。"""
    n = _norm(value)
    if not n:
        return True
    if n in blob:
        return True
    num = re.findall(r"-?\d+(?:\.\d+)?", n)
    if len(num) == 1 and len(num[0].lstrip("-")) >= 2:
        return re.search(r"(?<![\w.\-])" + re.escape(num[0]) + r"(?![\d.])", blob) is not None
    return False


def normalize_explicit_configs(req: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for c in req.get("explicit_configs") or []:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or "").strip()
        value = c.get("value")
        if not name and value in (None, ""):
            continue
        out.append({
            "req_id": str(req.get("req_id") or ""),
            "name": name,
            "value": value,
            "layer": str(c.get("layer") or ""),
            "target": str(c.get("target") or ""),
            "source_text": str(c.get("source_text") or ""),
        })
    return out


def restore_explicit_configs(final_reqs: List[Dict[str, Any]], parsed_reqs: List[Dict[str, Any]]) -> int:
    """综合评审 LLM 改写需求时可能丢掉 explicit_configs，按 req_id 从解析结果补回。返回补回条数。"""
    parsed = {str(r.get("req_id")): r for r in parsed_reqs or [] if isinstance(r, dict)}
    restored = 0
    for req in final_reqs or []:
        if not isinstance(req, dict):
            continue
        src = parsed.get(str(req.get("req_id")))
        if not src or not src.get("explicit_configs"):
            continue
        have = {(_norm(c.get("name")), _norm(c.get("value"))) for c in req.get("explicit_configs") or [] if isinstance(c, dict)}
        for c in src["explicit_configs"]:
            if isinstance(c, dict) and (_norm(c.get("name")), _norm(c.get("value"))) not in have:
                req.setdefault("explicit_configs", []).append(c)
                restored += 1
    return restored
