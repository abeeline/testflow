"""资料检索规则：多个来源怎么查、怎么排、怎么用。

来源（按可信度从高到低）：
    manual      用户在需求准备页粘贴的文字（只属于这条需求）
    kb_project  项目知识库（Dify，按项目配置）
    project     项目本地资料（TestFlow 里上传的临时资料）
    kb_public   公共知识库（Dify，3GPP / 运营商通用规范）
    public      公共本地资料

查询词：项目来源用需求原文；公共来源用从需求里提取的协议关键词（流程、消息、定时器、条款号），
因为 3GPP 资料按需求原文查效果很差。
"""
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCOPE_ORDER = ["manual", "kb_project", "project", "kb_public", "public"]
SCOPE_LABELS = {
    "manual": "用户粘贴",
    "kb_project": "项目知识库",
    "project": "项目本地资料",
    "kb_public": "公共知识库",
    "public": "公共本地资料",
}
# 每个来源最多带几条、每条最多多少字、自动检索部分总共最多多少字
MAX_HITS = {"kb_project": 4, "project": 4, "kb_public": 4, "public": 3}
MAX_HIT_CHARS = 700
MAX_TOTAL_CHARS = 6000

USAGE_RULE = (
    "【资料使用规则】可信度从高到低：用户粘贴 > 项目知识库 > 项目本地资料 > 公共知识库 > 公共本地资料。"
    "项目资料描述本产品的实际行为；公共资料（3GPP、运营商通用规范）只作通用默认值和条款依据。"
    "两者冲突时以项目资料为准，并在假设或风险里写明冲突。引用资料时写出编号，如 [K-3]。"
)

# 中文常用说法 → 3GPP 检索关键词
_TERM_MAP = {
    "重建": "RRC re-establishment", "重选": "cell reselection", "切换": "handover", "寻呼": "paging",
    "注册": "registration", "附着": "attach", "去附着": "detach", "鉴权": "authentication",
    "测量": "measurement", "驻留": "camping", "小区选择": "cell selection", "回落": "fallback",
    "载波聚合": "carrier aggregation", "双连接": "dual connectivity", "随机接入": "random access",
    "无线链路失败": "radio link failure", "波束": "beam management", "功控": "power control",
    "节电": "power saving", "省电": "power saving", "专用承载": "dedicated bearer", "默认承载": "default bearer",
    "会话": "PDU session", "跟踪区": "tracking area update", "漫游": "roaming", "紧急呼叫": "emergency call",
    "短信": "SMS", "语音": "voice", "能力上报": "UE capability", "系统消息": "system information",
    "接入禁止": "access barring", "拥塞": "congestion control", "定时器": "timer",
}
_TOKEN_PATTERNS = [
    r"\b(?:TS|TR)\s?\d{2}\.\d{3}\b",                      # TS 38.331
    r"\b\d{2}\.\d{3}\b",                                   # 36.523
    r"\b[TN]3\d{2,3}\b|\bT\d{3}\b",                        # T3412 / T311 / N310
    r"\b(?:RRC|NAS|EMM|ESM|5GMM|5GSM)[A-Za-z]*\b",
    r"\b[A-Z][a-z]+(?:[A-Z][a-z]+){1,}(?:Request|Complete|Reject|Accept|Command|Setup|Release|Reconfiguration|Indication|Response)?\b",  # RRCReconfiguration 之类的驼峰消息名
    r"\b(?:VoNR|VoLTE|EPS\s?FB|EPSFB|CSFB|SA|NSA|EN-?DC|NR-?DC|CA|DRX|eDRX|PSM|TAU|RAU|PDU|QoS|IMS|SIB\d*|MIB|RLF|HO|A[1-6]|B[12]|SRVCC|NB-IoT|LTE-M|Cat\.?\s?M1?)\b",
    r"\b[nb]\d{1,3}\b",                                    # 频段 n78 / b3
    r"(?:§|clause\s?|条款\s?)\d+(?:\.\d+)+",
]
_PRODUCT_WORDS = ("是否支持", "支持吗", "产品", "本项目", "该型号", "版本", "固件", "客户", "默认开启", "默认关闭", "配置项", "NV", "定制")


def extract_protocol_terms(text: str, limit: int = 16) -> List[str]:
    """从需求或问题文字里提取协议检索词（确定性规则，不调用大模型）。"""
    text = text or ""
    terms: List[str] = []
    for pat in _TOKEN_PATTERNS:
        for m in re.findall(pat, text):
            terms.append(m.strip())
    for zh, en in _TERM_MAP.items():
        if zh in text:
            terms.append(en)
    out: List[str] = []
    seen = set()
    for t in terms:
        k = t.lower()
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    return out[:limit]


def protocol_query(text: str, fallback: str = "") -> str:
    """公共知识库的查询词：协议关键词；一个都提不出来时退回原文。"""
    terms = extract_protocol_terms(text)
    return " ".join(terms) if terms else (fallback or text)


def is_product_question(question: str) -> bool:
    """产品行为类问题查项目知识库；纯协议问题（有协议关键词、没提产品）查公共知识库。"""
    q = question or ""
    if any(w in q for w in _PRODUCT_WORDS):
        return True
    return not extract_protocol_terms(q)


def format_context(manual: str, hits: Iterable[Dict[str, Any]], max_hits: Optional[Dict[str, int]] = None,
                   max_total: int = MAX_TOTAL_CHARS) -> Tuple[str, List[Dict[str, Any]]]:
    """按来源优先级排好检索结果，套上使用规则，控制条数和总字数。返回 (上下文, 实际用到的片段)。"""
    limits = {**MAX_HITS, **(max_hits or {})}
    by_scope: Dict[str, List[Dict[str, Any]]] = {s: [] for s in SCOPE_ORDER}
    for h in hits:
        scope = h.get("scope") if h.get("scope") in by_scope else "public"
        by_scope[scope].append(h)
    used: List[Dict[str, Any]] = []
    blocks: List[str] = []
    total = 0
    seen_text = set()
    for scope in SCOPE_ORDER[1:]:
        items = sorted(by_scope[scope], key=lambda x: x.get("score", 0), reverse=True)[: limits.get(scope, 3)]
        for h in items:
            text = re.sub(r"\s+", " ", str(h.get("text") or "")).strip()[:MAX_HIT_CHARS]
            key = text[:120]
            if not text or key in seen_text:
                continue
            if total + len(text) > max_total:
                break
            seen_text.add(key)
            total += len(text)
            ref = f"K-{len(used) + 1}"
            used.append({**h, "ref": ref, "scope_label": SCOPE_LABELS.get(scope, scope)})
            blocks.append(f"[{ref}] {SCOPE_LABELS.get(scope, scope)} · {h.get('filename', '')}\n{text}")
    parts: List[str] = []
    if manual.strip():
        parts.append("【用户粘贴的补充资料（最高优先级）】\n" + manual.strip())
    if blocks:
        parts.append(USAGE_RULE + "\n\n" + "\n\n".join(blocks))
    return "\n\n".join(parts), used


def ref_summary(hits: Iterable[Dict[str, Any]], **extra: Any) -> List[Dict[str, Any]]:
    """写进设计历史的引用清单（不存正文，只存来源、文档名和片段编号）。"""
    out = []
    for h in hits:
        item = {
            "ref": h.get("ref", ""),
            "scope": h.get("scope", ""),
            "scope_label": SCOPE_LABELS.get(h.get("scope", ""), ""),
            "filename": h.get("filename", ""),
            "chunk_id": h.get("chunk_id", ""),
            "score": h.get("score", 0),
        }
        item.update(extra)
        out.append(item)
    return out


_RESOLVE_SYSTEM = (
    "你是通信模组测试需求评审员。根据给出的资料片段判断评审问题能否直接得出答案。"
    "只依据资料，不要凭经验补充。只输出 JSON。"
)


def resolve_question(llm: Any, question: str, current_answer: str, scope: str, evidence: str,
                     kb_answer: str = "") -> Optional[Dict[str, Any]]:
    """让大模型根据知识库片段更新一个评审问题的答案。

    返回 {"status": "resolved"|"conflict"|"not_found", "answer", "basis"}；大模型不可用或解析失败时返回 None。
    """
    if not llm or not getattr(llm, "enabled", False) or not (evidence.strip() or kb_answer.strip()):
        return None
    user = (
        f"评审问题：{question}\n"
        f"评审员原先的默认答案：{current_answer or '无'}\n"
        f"资料来源：{SCOPE_LABELS.get(scope, scope)}\n"
        f"知识库的回答：{kb_answer[:800] or '无'}\n"
        f"资料片段：\n{evidence[:3000]}\n\n"
        "判断规则：资料明确给出答案 → resolved；资料与原先默认答案矛盾，或资料之间互相矛盾 → conflict；"
        "资料没有直接回答 → not_found。\n"
        '输出：{"status": "resolved|conflict|not_found", "answer": "简体中文答案，resolved/conflict 时必填", '
        '"basis": "依据的文档名和条款/章节"}'
    )
    try:
        text = llm.generate(_RESOLVE_SYSTEM, user, temperature=0, max_tokens=400)
        text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
        m = re.search(r"\{.*\}", text, flags=re.S)
        data = json.loads(m.group(0)) if m else {}
    except Exception:
        return None
    status = data.get("status")
    if status not in ("resolved", "conflict", "not_found"):
        return None
    return {"status": status, "answer": str(data.get("answer") or "").strip(), "basis": str(data.get("basis") or "").strip()}
