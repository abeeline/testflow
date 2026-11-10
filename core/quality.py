"""质量门：先做确定性修复，再判断是否需要让 LLM 返工，并且只返工有问题的部分。

设计稿：
    - 需求写明的配置没进 key_configuration → 直接补进该需求的矩阵行（不必重跑 LLM）
    - 需求的数值验收标准没进 pass_criteria → 直接补
    - 需求没有任何矩阵行 → 交给补漏（gap fill）调用，只为缺的需求生成行
    - P0/P1 需求只有正常流程 → 记为设计提示（不阻塞）
用例稿：
    - 需求写明的配置没进 TCD → 按 target 补进 configuration / message_contents
    - 结构问题（没有测试目的、没有判定点、协议环境没有小区配置或消息步骤……）→ 只返工这些用例对应的矩阵行
"""
from typing import Any, Dict, List, Tuple

from core.tcd import patch_explicit_configs
from utils.req_configs import blob_of, normalize_explicit_configs, value_present

PROTOCOL_ENVS = ("AMARISOFT", "PROTOCOL_ANALYZER")


def req_index(final_requirements: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(r.get("req_id")): r for r in final_requirements or [] if isinstance(r, dict) and r.get("req_id")}


def req_metrics(req: Dict[str, Any]) -> List[str]:
    acc = req.get("acceptance", {}) if isinstance(req, dict) else {}
    out = []
    for k in ("pass_fail", "kpi"):
        v = acc.get(k) if isinstance(acc, dict) else None
        out.extend(v if isinstance(v, list) else [])
    return [str(x) for x in out if str(x).strip() and str(x).strip() != "待补充"]


# ---------- 设计稿 ----------


def repair_design_rows(rows: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]]) -> Dict[str, int]:
    """把需求写明的配置和数值验收标准补进矩阵行。返回补入计数。"""
    reqs = req_index(final_requirements)
    patched_cfg = patched_metric = 0
    for row in rows:
        req = reqs.get(str(row.get("req_id")))
        if not req:
            continue
        cfg = row.setdefault("key_configuration", {})
        for c in normalize_explicit_configs(req):
            if not value_present(c["value"], blob_of(row, ["key_configuration", "scenario"])):
                key = c["name"] or "param"
                if key in cfg and cfg[key] != c["value"]:
                    key = f"{key}（需求值）"
                cfg[key] = c["value"]
                patched_cfg += 1
        crit = row.setdefault("pass_criteria", [])
        for m in req_metrics(req):
            if m not in crit:
                crit.append(m)
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
    env = str((tc.get("test_environment") or {}).get("primary") or "")
    if env in PROTOCOL_ENVS:
        if not (tc.get("configuration") or {}).get("cells"):
            issues.append("模拟基站/仪表用例缺少小区配置")
        if not any(p.get("message") for p in proc):
            issues.append("模拟基站/仪表用例没有信令消息步骤")
        ids = {m.get("msg_id") for m in tc.get("message_contents") or []}
        bad = [p.get("msg_ref") for p in proc if p.get("msg_ref") and p["msg_ref"] not in ids]
        if bad:
            issues.append(f"步骤引用了不存在的消息内容 {', '.join(bad[:3])}")
    return issues


def review_testcases(tcs: List[Dict[str, Any]], final_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """补入需求配置，检查结构和覆盖。返回 {issues, retry_rows, patched, per_tc}。"""
    reqs = req_index(final_requirements)
    per_tc: Dict[str, List[str]] = {}
    retry_rows: List[str] = []
    patched = 0
    covered = set()
    for tc in tcs:
        configs = []
        for rid in tc.get("trace", {}).get("req_ids") or []:
            covered.add(str(rid))
            if str(rid) in reqs:
                configs.extend(normalize_explicit_configs(reqs[str(rid)]))
        patched += len(patch_explicit_configs(tc, configs, value_present))
        issues = check_testcase(tc)
        if issues:
            per_tc[tc.get("tc_id", "")] = issues
            for ref in tc.get("trace", {}).get("source_refs") or []:
                if str(ref).startswith("ROW") and ref not in retry_rows:
                    retry_rows.append(ref)
    missing = [r for r in reqs if r not in covered]
    issues = [f"{k}: {'、'.join(v)}" for k, v in per_tc.items()]
    if missing:
        issues.append(f"用例 trace 缺少需求覆盖: {', '.join(missing)}")
    metrics_missing = []
    pass_text = " ".join(" ".join(tc.get("pass_fail") or []) for tc in tcs)
    for rid, req in reqs.items():
        for m in req_metrics(req):
            if any(ch.isdigit() for ch in m) and m not in pass_text:
                metrics_missing.append(m)
    return {"issues": issues, "retry_rows": retry_rows, "patched": patched, "per_tc": per_tc,
            "missing_reqs": missing, "metrics_missing": metrics_missing}


def feedback_for_rows(per_tc: Dict[str, List[str]], tcs: List[Dict[str, Any]], rows: List[str]) -> str:
    lines = []
    for tc in tcs:
        refs = set(tc.get("trace", {}).get("source_refs") or [])
        if refs & set(rows) and tc.get("tc_id") in per_tc:
            lines.append(f"{'/'.join(sorted(refs))}（上次 {tc['tc_id']}）: {'、'.join(per_tc[tc['tc_id']])}")
    return "上一次生成的用例有以下问题，请针对这些矩阵行重新生成并逐条改正：\n" + "\n".join(lines) if lines else ""


def split_tcs_by_rows(tcs: List[Dict[str, Any]], rows: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    keep, drop = [], []
    rs = set(rows)
    for tc in tcs:
        (drop if set(tc.get("trace", {}).get("source_refs") or []) & rs else keep).append(tc)
    return keep, drop
