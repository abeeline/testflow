"""测试类型：功能 / 性能 / 稳定性。

在需求页勾选，随 product_profile.test_types 贯穿整个流程：
- 需求解析和规范评审：选了性能就要把 KPI（指标、目标值、样本量、统计口径）提出来，没有就列成待确认问题；
  选了稳定性就要问清时长 / 循环次数和恢复判据；
- 测试设计：选中的类型按模块（一级分组）至少各有一个测试点，没选的类型不主动设计；
- 质量门和测试架构图：选了但某个模块没有对应测试点时，作为关注点列出来。

测试点的类型由 technique 决定：performance → 性能，stability → 稳定性，其余都是功能。
"""
from typing import Any, Dict, List

from core.grouping import UNGROUPED, requirement_group

TEST_TYPES = ["functional", "performance", "stability"]
TEST_TYPE_LABELS = {"functional": "功能", "performance": "性能", "stability": "稳定性"}
_ALIASES = {"功能": "functional", "function": "functional", "性能": "performance", "kpi": "performance",
            "稳定性": "stability", "稳定": "stability", "鲁棒性": "stability", "robustness": "stability", "长稳": "stability"}
_GUIDE = {
    "functional": "功能：按测试技术（normal / abnormal / boundary / timer / collision / mobility / interworking / capability）导出测试点。",
    "performance": "性能：每个模块（需求的 group 一级，没有分组时指整份需求）至少一个 technique=performance 的测试点，"
                   "写明被测指标（时延 / 成功率 / 吞吐 / 精度）、测量起止点、样本量和统计口径（如 20 次取均值和最大值、P95）、目标值；"
                   "需求没有给目标值时用“建议值”并注明待项目确认，不要当成已批准的验收门限。",
    "stability": "稳定性：每个模块至少一个 technique=stability 的测试点（长时间保持、反复执行同一流程、异常后恢复三选一或组合），"
                 "写明时长或循环次数、过程中持续检查的项（掉话、复位、状态残留、内存）、允许的失败次数和恢复判据。",
}


def normalize_test_types(value: Any) -> List[str]:
    items = value if isinstance(value, (list, tuple, set)) else [value] if value else []
    picked = {_ALIASES.get(str(x).strip().lower(), str(x).strip().lower()) for x in items}
    out = [t for t in TEST_TYPES if t in picked]
    return out or ["functional"]


def selected_test_types(shared: Any) -> List[str]:
    """从流程上下文（shared）或产品画像里取勾选的测试类型；没选时只做功能。"""
    shared = shared if isinstance(shared, dict) else {}
    profile = shared.get("product_profile") if isinstance(shared.get("product_profile"), dict) else {}
    return normalize_test_types(shared.get("test_types") or profile.get("test_types"))


def type_of_technique(technique: Any) -> str:
    key = str(technique or "").strip().lower()
    return key if key in ("performance", "stability") else "functional"


def scope_note(selected: List[str]) -> str:
    """写进提示词的说明。"""
    selected = normalize_test_types(selected)
    lines = ["本次测试范围（test_types）：" + "、".join(TEST_TYPE_LABELS[t] for t in selected) + "。"]
    lines += [_GUIDE[t] for t in selected]
    skipped = [TEST_TYPE_LABELS[t] for t in TEST_TYPES if t not in selected]
    if skipped:
        lines.append("没有选的类型（" + "、".join(skipped) + "）不主动设计；需求原文明确提出了这类指标时照常保留。")
    return "\n".join(lines)


def review_note(selected: List[str]) -> str:
    """给需求解析 / 规范评审的说明：这一步要把后面设计用得上的指标问出来。"""
    selected = normalize_test_types(selected)
    lines = ["本次测试范围（test_types）：" + "、".join(TEST_TYPE_LABELS[t] for t in selected) + "。"]
    if "performance" in selected:
        lines.append("范围包含性能：需求里的时延、成功率、吞吐、精度等指标要完整提取到 acceptance.kpi；"
                     "需求只有“快速”“缩短”“提升”这类定性描述、没有目标值时，提一个待确认问题（指标、目标值、样本量），并在 ai_answer 给出建议值。")
    if "stability" in selected:
        lines.append("范围包含稳定性：检查需求是否给出了长时间运行、反复执行、异常恢复方面的要求（时长 / 次数 / 恢复时间）；"
                     "没有时提一个待确认问题，并在 ai_answer 给出建议的时长或循环次数。")
    return "\n".join(lines)


def type_gaps(rows: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]], selected: List[str]) -> List[Dict[str, str]]:
    """选中的性能 / 稳定性在哪些模块还没有测试点。返回 [{"module", "test_type", "text"}]。"""
    selected = [t for t in normalize_test_types(selected) if t != "functional"]
    if not selected:
        return []
    module_of = {str(r.get("req_id")): requirement_group(r)[0] for r in final_requirements or [] if isinstance(r, dict)}
    modules = list(dict.fromkeys(module_of.values()))
    if not modules:
        return []
    have: Dict[str, set] = {}
    for row in rows or []:
        rid = row.get("req_id")
        rid = str(rid[0] if isinstance(rid, list) and rid else rid)
        have.setdefault(module_of.get(rid, UNGROUPED), set()).add(type_of_technique(row.get("technique")))
    return [{"module": m, "test_type": t, "text": f"{m}：选了{TEST_TYPE_LABELS[t]}测试，但这个模块没有{TEST_TYPE_LABELS[t]}测试点"}
            for m in modules for t in selected if t not in have.get(m, set())]
