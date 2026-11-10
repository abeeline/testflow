"""质量门：先做确定性修复，再判断是否需要让 LLM 返工，并且只返工有问题的部分。

设计稿：
    - 需求写明的配置没进 key_configuration → 直接补进该需求的矩阵行（不必重跑 LLM）
    - 需求的验收门限没被任何一行带上 → 补进该需求的正常流程行
    - 需求没有任何矩阵行 → 交给补漏（gap fill）调用，只为缺的需求生成行
    - P0/P1 需求只有正常流程 → 记为设计提示（不阻塞）
用例稿：
    - 需求写明的配置没进 TCD → 按 target 补进 configuration / message_contents；同名取值不同 → 标冲突并让 LLM 改一次
    - 矩阵行的数值门限没进 pass_fail → 直接补
    - 结构问题（没有测试目的、没有判定点、协议环境没有小区配置或消息步骤……）→ 只返工这些用例对应的矩阵行
    - LLM 专家评审（nodes.py 里调用）指出的严重问题 → 并入返工反馈；一般问题记到用例的 review_notes
"""
import re
from typing import Any, Dict, List, Tuple

from core.tcd import patch_explicit_configs
from utils.req_configs import config_status, group_configs, normalize_explicit_configs

PROTOCOL_ENVS = ("AMARISOFT", "PROTOCOL_ANALYZER")
_ROW_CONFIG_FIELDS = ["key_configuration", "scenario", "test_purpose"]
_NUMBER = re.compile(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?")  # T3346、n78 这类标识符里的数字不算门限


def req_index(final_requirements: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(r.get("req_id")): r for r in final_requirements or [] if isinstance(r, dict) and r.get("req_id")}


def req_metrics(req: Dict[str, Any]) -> List[str]:
    acc = req.get("acceptance", {}) if isinstance(req, dict) else {}
    out = []
    for k in ("pass_fail", "kpi"):
        v = acc.get(k) if isinstance(acc, dict) else None
        out.extend(v if isinstance(v, list) else [])
    return [str(x) for x in out if str(x).strip() and str(x).strip() != "待补充"]


def _squash(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower()


def criterion_covered(criterion: str, texts: List[str]) -> bool:
    """一条通过标准是否已被带上：原文出现，或其中的数值门限（如 10、99、-110）都出现了（表述可以不同）。"""
    blob = _squash(" ".join(str(t) for t in texts))
    if _squash(criterion) in blob:
        return True
    numbers = _NUMBER.findall(str(criterion))
    if not any(len(n.replace(".", "")) >= 2 for n in numbers):
        return False  # 只有个位数（或没有数字）时不好按数字比对，要求原文出现
    return all(re.search(r"(?<![\d.])" + re.escape(n) + r"(?![\d.])", blob) for n in numbers)


def uncovered_thresholds(criteria: List[Any], texts: List[str]) -> List[str]:
    """criteria 里带数值门限、但没有出现在 texts 里的条目。"""
    return [str(c).strip() for c in criteria or [] if _NUMBER.search(str(c)) and not criterion_covered(str(c), texts)]


# ---------- 设计稿 ----------


def repair_design_rows(rows: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]]) -> Dict[str, int]:
    """把需求写明的配置和验收门限补进矩阵行。返回补入计数。"""
    reqs = req_index(final_requirements)
    patched_cfg = patched_metric = 0
    by_req: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        req = reqs.get(str(row.get("req_id")))
        if not req:
            continue
        by_req.setdefault(str(row.get("req_id")), []).append(row)
        cfg = row.setdefault("key_configuration", {})
        for group in group_configs(normalize_explicit_configs(req)):
            states = [config_status(c, row, _ROW_CONFIG_FIELDS) for c in group]
            name = group[0]["name"] or "param"
            if len(group) > 1:  # 需求给了一组取值：本行用到其中一个就行，一个都没有就把整组列出来
                if not any(st["status"] == "applied" for st in states):
                    cfg[f"{name}（需求取值）" if name in cfg else name] = [c["value"] for c in group]
                    patched_cfg += 1
                continue
            if states[0]["status"] != "applied":
                # 行里同名但取值不同（如边界值测试点）时不覆盖，需求值另存
                cfg[f"{name}（需求值）" if states[0]["status"] == "conflict" else name] = group[0]["value"]
                patched_cfg += 1
    # 验收门限：每条至少被该需求的一个测试点带上；没有的补到正常流程行（没有正常流程就补到第一行）
    for rid, req_rows in by_req.items():
        targets = [r for r in req_rows if r.get("technique") == "normal"] or req_rows[:1]
        for m in req_metrics(reqs[rid]):
            if any(criterion_covered(m, r.get("pass_criteria") or []) for r in req_rows):
                continue
            for r in targets:
                r.setdefault("pass_criteria", []).append(m)
            patched_metric += 1
    return {"configs": patched_cfg, "metrics": patched_metric}


def design_gaps(rows: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]],
                objectives: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    req_ids = list(req_index(final_requirements).keys())
    covered = {str(r.get("req_id")) for r in rows}
    obj_covered = {str(r.get("objective_id")) for r in rows}
    return {
        "missing_reqs": [r for r in req_ids if r not in covered],
        "missing_objectives": [str(o.get("objective_id")) for o in objectives
                               if isinstance(o, dict) and str(o.get("objective_id")) not in obj_covered],
    }


def design_advice(rows: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]]) -> List[str]:
    """不阻塞的设计提示：高优先级需求只覆盖了正常流程。"""
    out = []
    by_req: Dict[str, set] = {}
    for r in rows:
        by_req.setdefault(str(r.get("req_id")), set()).add(str(r.get("technique") or "normal"))
    for rid, req in req_index(final_requirements).items():
        if str(req.get("priority")) in ("P0", "P1") and by_req.get(rid) and by_req[rid] <= {"normal"}:
            out.append(f"{rid} 为 {req.get('priority')} 需求，但只设计了正常流程，建议补充异常/边界/定时器场景")
    return out


# ---------- 用例稿 ----------


def check_testcase(tc: Dict[str, Any]) -> List[str]:
    issues = []
    tp = tc.get("test_purpose") or {}
    if not tp.get("when") or not tp.get("then"):
        issues.append("测试目的缺少 when/then")
    proc = tc.get("procedure") or []
    if len(proc) < 2:
        issues.append("测试步骤少于 2 步")
    if not any(p.get("verdict") and p.get("expected") for p in proc):
        issues.append("没有带期望结果的判定步骤")
    if not [x for x in tc.get("pass_fail") or [] if x and x != "待补充通过条件"]:
        issues.append("缺少通过标准")
    ids = {m.get("msg_id") for m in tc.get("message_contents") or []}
    bad = [p.get("msg_ref") for p in proc if p.get("msg_ref") and p["msg_ref"] not in ids]
    if bad:
        issues.append(f"步骤引用了不存在的消息内容 {', '.join(bad[:3])}")
    env = str((tc.get("test_environment") or {}).get("primary") or "")
    if env in PROTOCOL_ENVS:
        if not (tc.get("configuration") or {}).get("cells"):
            issues.append("模拟基站/仪表用例缺少小区配置")
        if not any(p.get("message") for p in proc):
            issues.append("模拟基站/仪表用例没有信令消息步骤")
    return issues


def ensure_pass_criteria(tc: Dict[str, Any], row: Dict[str, Any]) -> int:
    """矩阵行里带数值门限的通过标准必须进用例的 pass_fail；LLM 漏了或改弱了就按原文补上。返回补入条数。"""
    pass_fail = [x for x in tc.get("pass_fail") or [] if x and x != "待补充通过条件"]
    missing = uncovered_thresholds(row.get("pass_criteria"), pass_fail)
    if missing:
        tc["pass_fail"] = pass_fail + missing
    return len(missing)


def review_testcases(tcs: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]],
                     rows: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """补入需求配置和数值门限，检查结构和覆盖。

    返回 {issues, per_tc, retry_rows, patched, conflicts, criteria_added, missing_reqs, metrics_missing}。
    per_tc 里的问题都值得让 LLM 返工一次；返工后仍然存在的，确定性修复的结果（补入 / 冲突标记）已经留在用例里。
    """
    reqs = req_index(final_requirements)
    row_map = {str(r.get("row_id")): r for r in rows or [] if isinstance(r, dict)}
    per_tc: Dict[str, List[str]] = {}
    retry_rows: List[str] = []
    patched = conflicts = criteria_added = 0
    covered = set()
    for tc in tcs:
        trace = tc.get("trace") or {}
        configs = []
        for rid in trace.get("req_ids") or []:
            covered.add(str(rid))
            if str(rid) in reqs:
                configs.extend(normalize_explicit_configs(reqs[str(rid)]))
        issues = check_testcase(tc)
        for r in patch_explicit_configs(tc, configs):
            if r["status"] == "patched":
                patched += 1
            elif r["status"] == "conflict":
                conflicts += 1
                issues.append(f"需求写明 {r['name']}={r['value']}，{r['note']}；请按需求值改正，"
                              "若本用例有意改变该参数，请把它列入 parameter_variations 并说明")
        refs = [str(x) for x in trace.get("source_refs") or []]
        for ref in refs:
            if ref in row_map:
                criteria_added += ensure_pass_criteria(tc, row_map[ref])
        if issues:
            per_tc[tc.get("tc_id", "")] = issues
            for ref in refs:
                if (ref in row_map or (not row_map and ref.startswith("ROW"))) and ref not in retry_rows:
                    retry_rows.append(ref)
    missing = [r for r in reqs if r not in covered]
    issues = [f"{k}: {'、'.join(v)}" for k, v in per_tc.items()]
    if missing:
        issues.append(f"用例 trace 缺少需求覆盖: {', '.join(missing)}")
    metrics_missing = []
    for rid, req in reqs.items():
        texts = [x for tc in tcs if rid in [str(r) for r in (tc.get("trace") or {}).get("req_ids") or []]
                 for x in tc.get("pass_fail") or []]
        metrics_missing.extend(m for m in req_metrics(req) if _NUMBER.search(m) and not criterion_covered(m, texts))
    return {"issues": issues, "retry_rows": retry_rows, "patched": patched, "conflicts": conflicts,
            "criteria_added": criteria_added, "per_tc": per_tc, "missing_reqs": missing,
            "metrics_missing": metrics_missing}


def review_stats(tcs: List[Dict[str, Any]]) -> Dict[str, int]:
    """整份用例里需求配置的落地统计（按 requirement_configs 的 status 计数）。"""
    out: Dict[str, int] = {"applied": 0, "patched": 0, "conflict": 0, "varied": 0}
    for tc in tcs:
        for r in tc.get("requirement_configs") or []:
            if r.get("status") in out:
                out[r["status"]] += 1
    return out


def merge_expert_review(per_tc: Dict[str, List[str]], tcs: List[Dict[str, Any]], reviews: List[Dict[str, Any]]) -> Dict[str, int]:
    """把 LLM 专家评审并入质量门结果：major 问题进 per_tc（触发返工），其余写到用例的 review_notes（页面可见）。"""
    by_id = {tc.get("tc_id"): tc for tc in tcs}
    major = minor = 0
    for rv in reviews or []:
        tc = by_id.get(str(rv.get("tc_id") or ""))
        if not tc:
            continue
        for it in rv.get("issues") or []:
            if not isinstance(it, dict) or not str(it.get("problem") or "").strip():
                continue
            text = str(it["problem"]).strip()
            if it.get("field"):
                text = f"[{it['field']}] {text}"
            if it.get("suggestion"):
                text += f"；建议：{str(it['suggestion']).strip()}"
            if str(it.get("severity") or "").lower() == "major":
                per_tc.setdefault(tc["tc_id"], []).append(f"专家评审：{text}")
                major += 1
            else:
                notes = tc.setdefault("review_notes", [])
                if text not in notes:
                    notes.append(text)
                minor += 1
    return {"major": major, "minor": minor}


def rows_for_tcs(per_tc: Dict[str, List[str]], tcs: List[Dict[str, Any]], valid_rows: set) -> List[str]:
    out: List[str] = []
    for tc in tcs:
        if tc.get("tc_id") in per_tc:
            out.extend(r for r in (tc.get("trace") or {}).get("source_refs") or [] if r in valid_rows and r not in out)
    return out


def feedback_for_rows(per_tc: Dict[str, List[str]], tcs: List[Dict[str, Any]], rows: List[str]) -> str:
    lines = []
    for tc in tcs:
        refs = set(tc.get("trace", {}).get("source_refs") or [])
        if refs & set(rows) and tc.get("tc_id") in per_tc:
            lines.append(f"{'/'.join(sorted(refs))}（上次 {tc['tc_id']}）: {'；'.join(per_tc[tc['tc_id']])}")
    return "上一次生成的用例有以下问题，请针对这些矩阵行重新生成并逐条改正：\n" + "\n".join(lines) if lines else ""


def split_tcs_by_rows(tcs: List[Dict[str, Any]], rows: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    keep, drop = [], []
    rs = set(rows)
    for tc in tcs:
        (drop if set(tc.get("trace", {}).get("source_refs") or []) & rs else keep).append(tc)
    return keep, drop

