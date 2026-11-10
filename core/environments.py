"""测试环境：目录、能力边界与推荐规则。

能力边界（capabilities / limits）会带进测试设计和用例生成的提示词，
让 LLM 按“这个环境能控制什么、不能控制什么”选择环境，而不是只凭关键词。
"""
from typing import Any, Dict, List

from schemas import TEST_ENVIRONMENT_CATALOG

ENVIRONMENT_CAPABILITIES = {
    "REAL_NETWORK": {
        "can": ["运营商真实网络与 SIM", "用户操作与业务体验（UI / AT 指令）", "长稳、功耗、互通、漫游"],
        "cannot": ["控制基站参数或下发指定 IE", "构造异常信令或指定拒绝原因", "精确控制定时器"],
        "executor": "Artemis（手机）/ AT Agent（模组）",
    },
    "AMARISOFT": {
        "can": ["小区/PHY 参数（band、ARFCN、带宽、SCS、TDD、功率）", "核心网接受/拒绝及 cause、NAS 定时器、PSM/eDRX",
                "SIB 与常用 RRC/NAS 字段定制", "小区功率变化、切换、寻呼、释放等可脚本化流程"],
        "cannot": ["任意 ASN.1 字段级畸形消息", "仪表级精确时序与一致性判定"],
        "executor": "Amarisoft Agent（自行生成 enb/gnb/mme 配置并执行）",
    },
    "PROTOCOL_ANALYZER": {
        "can": ["逐条消息模板 + IE 覆盖值", "异常/畸形信令注入、定时器与时序精确控制", "一致性风格的逐步判定"],
        "cannot": ["真实运营商网络行为", "大规模长稳与用户体验"],
        "executor": "PRTest（消息模板 XML + Python 流程）",
    },
}


def environment_label(env_id: str) -> str:
    return TEST_ENVIRONMENT_CATALOG.get(env_id, {}).get("label", env_id or "未指定环境")


def normalize_available(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    selected = raw.get("selected_ids") or raw.get("selected") or []
    if not isinstance(selected, list):
        selected = []
    normalized = [str(x) for x in selected if str(x) in TEST_ENVIRONMENT_CATALOG]
    return {
        "selected_ids": normalized,
        "selected_details": [TEST_ENVIRONMENT_CATALOG[x] for x in normalized],
        "selected_count": len(normalized),
    }


def environment_brief(available: Any) -> Dict[str, Any]:
    """给提示词用的环境说明：用户勾选了哪些，每个环境能做/不能做什么。"""
    sel = normalize_available(available)["selected_ids"]
    return {
        "selected_ids": sel,
        "catalog": {
            k: {"label": v["label"], **ENVIRONMENT_CAPABILITIES.get(k, {}), "selected": k in sel}
            for k, v in TEST_ENVIRONMENT_CATALOG.items()
        },
    }


_PROTOCOL_KEYWORDS = ["ie", "timer", "reject", "cause", "protocol", "nas", "rrc", "emm", "esm",
                      "信令", "协议", "定时器", "原因码", "异常注入", "流程构建", "ie配置", "协议栈"]
_REAL_KEYWORDS = ["现网", "实网", "运营商", "用户体验", "用户操作", "真实网络", "长稳", "ui", "业务连续性", "真实sim"]
_AMARI_KEYWORDS = ["amarisoft", "l3", "phy", "基础注册", "基础附着", "基础协议", "基础移动性", "仿真", "模拟基站"]


def recommend(texts: List[str], available_envs: Any) -> Dict[str, Any]:
    """LLM 没给出合法环境时的规则兜底。"""
    selected_ids = normalize_available(available_envs)["selected_ids"]
    text = " ".join(str(x) for x in texts if str(x).strip()).lower()
    required, rationale = "AMARISOFT", "当前场景偏向可重复、可控的基础协议与接入验证，优先使用Amarisoft模拟基站。"
    if any(k in text for k in _PROTOCOL_KEYWORDS):
        required, rationale = "PROTOCOL_ANALYZER", "当前场景需要精确协议流程控制、IE配置或异常注入，更适合使用协议分析仪表。"
    elif any(k in text for k in _REAL_KEYWORDS):
        required, rationale = "REAL_NETWORK", "当前场景关注真实运营商网络与用户操作体验，优先使用实网环境。"
    elif any(k in text for k in _AMARI_KEYWORDS):
        rationale = "当前场景偏向基础PHY/L3仿真与可重复回归，优先使用Amarisoft模拟基站。"
    if selected_ids:
        risk = "" if required in selected_ids else (
            f"当前建议环境为{environment_label(required)}，但用户未勾选该环境；若测试团队当前不可用，需要补齐环境或调整覆盖策略。")
        alternatives = [x for x in selected_ids if x != required]
    else:
        risk = "用户未勾选任何测试环境，当前按场景必要性推荐环境；请测试团队确认资源可用性。"
        alternatives = [x for x in TEST_ENVIRONMENT_CATALOG if x != required]
    return {
        "primary": required,
        "primary_label": environment_label(required),
        "alternatives": alternatives,
        "alternative_labels": [environment_label(x) for x in alternatives],
        "rationale": rationale,
        "availability_risk": risk,
    }


def normalize_env(env: Any, fallback_texts: List[str], available_envs: Any, linked: Any = None) -> Dict[str, Any]:
    """统一测试环境字段：合法就补齐标签，不合法先用 linked（矩阵行的环境），再按规则推荐。"""
    if isinstance(env, str):
        env = {"primary": env}
    if not isinstance(env, dict):
        env = {}
    primary = str(env.get("primary", "")).strip().upper()
    if primary not in TEST_ENVIRONMENT_CATALOG:
        if isinstance(linked, dict) and str(linked.get("primary", "")) in TEST_ENVIRONMENT_CATALOG:
            return linked
        return recommend(fallback_texts, available_envs)
    alts = [str(x) for x in (env.get("alternatives") or []) if str(x) in TEST_ENVIRONMENT_CATALOG]
    sel = normalize_available(available_envs)["selected_ids"]
    risk = env.get("availability_risk") or env.get("risk") or ""
    if sel and primary not in sel and not risk:
        risk = f"推荐环境{environment_label(primary)}未勾选，需要补齐环境或调整覆盖策略。"
    return {
        "primary": primary,
        "primary_label": env.get("primary_label") or environment_label(primary),
        "alternatives": alts,
        "alternative_labels": env.get("alternative_labels") or [environment_label(x) for x in alts],
        "rationale": env.get("rationale") or env.get("reason") or "",
        "availability_risk": risk,
    }
