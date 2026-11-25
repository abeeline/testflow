"""需求澄清与定稿：回答核对、写回需求、定稿闸门、影响分析、Excel 回填、一致性 / 歧义检查、规范表插件。"""
import asyncio
import copy

import pytest

from core import clarify_stage as C
from core import spec_checkers
from core.clarification import build_clarifications
from core.req_checks import restatement_cards


def _req(rid="AR-1", **kw):
    base = {"req_id": rid, "title": f"需求 {rid}", "description": "", "constraints": ["3GPP Release：R17"],
            "preconditions": ["UE 驻留 NTN 小区"], "trigger": ["SS 下发 SIB1"], "expected": ["UE 按配置执行"],
            "acceptance": {"pass_fail": ["UE 发出 RRCSetupRequest"]}, "explicit_configs": [], "group": ["SR 1"]}
    base.update(kw)
    return base


def _spec(reqs, items):
    spec = {"final_requirements": reqs, "clarifications": {"items": items}}
    C.refresh(spec)
    return spec


def _item(cid, rid="AR-1", kind="unknown_field", field="", blocking=True, status="open", suggestion=""):
    return {"id": cid, "req_id": rid, "kind": kind, "field": field, "question": f"{field} 有问题", "blocking": blocking,
            "status": status, "evidence": "", "suggestion": suggestion, "raised_by": ["ASN.1 核对"], "source_text": "",
            "resolution": ""}


# ---------- 回答核对 ----------

def test_answer_with_invented_field_is_rejected():
    v = C.verify_answer(_item("CLR-1", field="enhancedMeasurementLEO-r17"), "改为 enhancedMeasurementFOO-r17")
    assert v["level"] == "reject" and "不存在" in v["notes"][0]


def test_answer_rename_and_remove():
    v = C.verify_answer(_item("CLR-1", field="enhancedMeasurementLEO-r17"), "替换为 enhancedMeasurementNGSO-r17（ENUMERATED {true}）")
    assert v["level"] == "ok" and v["rename_to"] == "enhancedMeasurementNGSO-r17"
    v = C.verify_answer(_item("CLR-2", field="ra-ContentionResolutionTimerExt-r18"),
                        "删除不存在的 ra-ContentionResolutionTimerExt-r18。RRC 用标准 ra-ContentionResolutionTimer")
    assert v["level"] == "ok" and v["remove"] and not v["rename_to"]


def test_answer_slash_shorthand_is_expanded():
    v = C.verify_answer(_item("CLR-1", field="x-r18"), "校验 BWP-UplinkCommon 下的 rsrp-ThresholdMsg1-RepetitionNum2/4/8-r18")
    assert v["level"] != "reject", v["notes"]


def test_answer_wrong_location_is_corrected():
    # 需求方说 nonTerrestrialNetwork-r17 在 BandNR 下；规范里在 UE-NR-Capability-v1700
    v = C.verify_answer(_item("CLR-1", field="ntnSupport-r17"), "UE 能力用 BandNR 下的 nonTerrestrialNetwork-r17")
    assert v["level"] == "corrected" and "UE-NR-Capability-v1700" in "".join(v["notes"])


def test_value_answer_must_be_encodable():
    it = _item("CLR-1", kind="value_type", field="numberOfMsg4HARQ-ACK-Repetitions-r18")
    assert C.verify_answer(it, "{n2, n4, n8}")["level"] == "reject"
    v = C.verify_answer(it, "'1010'B")
    assert v["level"] == "ok" and v["value"] == "'1010'B"


# ---------- 回填、写回、确认 ----------

def test_apply_answers_rewrites_requirement_and_resets_confirmation():
    req = _req(expected=["UE 按 enhancedMeasurementLEO-r17 放宽测量"],
               explicit_configs=[{"name": "enhancedMeasurementLEO-r17", "value": "true", "source_text": "原文 enhancedMeasurementLEO-r17"}])
    spec = _spec([req], [_item("CLR-1", field="enhancedMeasurementLEO-r17")])
    C.apply_answers(spec, [], confirmations={"AR-1": {"confirmed": True}}, by="张三")
    assert C.gate_status(spec)["unconfirmed"] == []
    res = C.apply_answers(spec, [{"id": "CLR-1", "answer": "替换为 enhancedMeasurementNGSO-r17"}], by="张三")
    assert res["applied"] and not res["rejected"]
    cfg = spec["final_requirements"][0]["explicit_configs"][0]
    assert cfg["name"] == "enhancedMeasurementNGSO-r17" and cfg["fixed_from"] == "enhancedMeasurementLEO-r17"
    assert "enhancedMeasurementLEO-r17" in cfg["source_text"]  # 需求原文不改
    assert "enhancedMeasurementNGSO-r17" in spec["final_requirements"][0]["expected"][0]
    assert spec["clarifications"]["pending_req_ids"] == []
    # 需求改了，理解确认要重来
    assert C.gate_status(spec)["unconfirmed"] == ["AR-1"]
    assert spec["clarifications"]["items"][0]["status"] == "resolved_by_owner"


def test_apply_rejects_bad_answer_and_ai_answers():
    spec = _spec([_req()], [_item("CLR-1", field="foo-r17"), _item("CLR-2", field="bar-r17")])
    res = C.apply_answers(spec, [{"id": "CLR-1", "answer": "改为 notAField-r17"},
                                 {"id": "CLR-2", "answer": "按默认", "source": "AI 建议"},
                                 {"id": "CLR-9", "answer": "x"}])
    assert [r["id"] for r in res["rejected"]] == ["CLR-1"]
    assert {s["id"] for s in res["skipped"]} == {"CLR-2", "CLR-9"}
    assert spec["clarifications"]["pending_req_ids"] == ["AR-1"]


def test_waive_accept_reopen():
    items = [_item("CLR-1", field="foo-r17"), _item("CLR-2", kind="renamed", field="ta-Info", blocking=False, suggestion="ta-Info-r17")]
    spec = _spec([_req()], items)
    C.apply_answers(spec, [{"id": "CLR-1", "action": "waive", "answer": "本轮不测"}, {"id": "CLR-2", "action": "accept"}], apply_spec=False)
    st = {it["id"]: it["status"] for it in spec["clarifications"]["items"]}
    assert st == {"CLR-1": "waived", "CLR-2": "resolved_by_owner"}
    assert not spec["clarifications"]["pending_req_ids"]
    C.apply_answers(spec, [{"id": "CLR-1", "action": "reopen"}])
    assert spec["clarifications"]["pending_req_ids"] == ["AR-1"]


def test_spec_fixes_are_written_back():
    req = _req(expected=["星历、ta-Info 更新不改变 valueTag"],
               explicit_configs=[{"name": "rsrp-ThresholdMsg1-RepetitionNum2-r18", "value": "-115 dBm"}])
    items = [_item("CLR-1", kind="renamed", field="ta-Info", blocking=False, status="resolved_by_spec", suggestion="ta-Info-r17"),
             _item("CLR-2", kind="value_type", field="rsrp-ThresholdMsg1-RepetitionNum2-r18", blocking=False,
                   status="resolved_by_spec", suggestion="rsrp-ThresholdMsg1-RepetitionNum2-r18 = 41（-115 dBm）")]
    spec = _spec([req], items)
    changes = C.apply_spec_fixes(spec)
    assert "ta-Info-r17" in req["expected"][0]
    assert req["explicit_configs"][0]["value"] == 41 and req["explicit_configs"][0]["value_from"] == "-115 dBm"
    assert len(changes) == 2 and not C.apply_spec_fixes(spec)  # 不重复写


# ---------- 定稿 ----------

def test_freeze_gate_and_stale_baseline():
    spec = _spec([_req()], [_item("CLR-1", field="foo-r17")])
    ok, info = C.freeze(spec, confirmer="张三")
    assert not ok and "阻塞" in info["reason"]
    assert not C.freeze(spec, confirmer="")[0]
    C.apply_answers(spec, [{"id": "CLR-1", "action": "waive"}], confirmations={"AR-1": True})
    ok, g = C.freeze(spec, confirmer="张三", note="评审会结论")
    assert ok and g["frozen"] and g["design_allowed"] and g["baseline"]["version"] == 1
    # 定稿后再改需求：基线过期，设计闸门关上
    C.apply_answers(spec, [{"id": "CLR-1", "action": "reopen"}])
    g = C.gate_status(spec)
    assert g["stale"] and not g["design_allowed"]
    ok, g = C.freeze(spec, confirmer="李四", allow_pending=True)
    assert ok and g["baseline"]["version"] == 2 and g["baseline"]["allow_pending"]
    assert spec["baseline"]["history"][0]["version"] == 1


def test_design_stage_requires_frozen_baseline():
    from fastapi import HTTPException

    import main

    spec = _spec([_req()], [_item("CLR-1", field="foo-r17")])
    with pytest.raises(HTTPException) as e:
        asyncio.run(main.stage_start("design", main.StageGenerateRequest(requirement_spec=spec)))
    assert e.value.status_code == 409 and e.value.detail["code"] == "requirements_not_frozen"


# ---------- 影响分析 ----------

def test_impact_marks_downstream_stale():
    changes = [{"req_id": "AR-1", "clr_id": "CLR-1", "path": "explicit_configs[0].name",
                "before": "enhancedMeasurementLEO-r17", "after": "enhancedMeasurementNGSO-r17"}]
    design = {"integrated_matrix": [{"row_id": "R-1", "req_id": "AR-1"}, {"row_id": "R-2", "req_id": "AR-2"}]}
    cases = {"testcases": [{"tc_id": "TC-1", "steps": ["配置 enhancedMeasurementLEO-r17 = true"]}, {"tc_id": "TC-2", "steps": []}]}
    imp = C.impact(changes, test_design_spec=design, test_case_spec=cases)
    assert imp["by_artifact"] == {"测试设计": ["R-1"], "测试用例": ["TC-1"]}
    assert design["integrated_matrix"][0]["stale"] and "stale" not in design["integrated_matrix"][1]
    assert imp["plan"]


# ---------- Excel ----------

def test_xlsx_round_trip():
    spec = _spec([_req()], [_item("CLR-1", field="foo-r17"), _item("CLR-2", field="bar-r17")])
    data = C.export_xlsx(spec)
    from io import BytesIO

    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(data))
    ws = wb["需求澄清"]
    head = [c.value for c in ws[1]]
    ws.cell(row=2, column=head.index("需求方回答") + 1, value="改为 ra-ContentionResolutionTimer")
    ws.cell(row=3, column=head.index("处理方式") + 1, value="豁免")
    ws.cell(row=3, column=head.index("回答人") + 1, value="王五")
    buf = BytesIO()
    wb.save(buf)
    answers = C.import_xlsx(buf.getvalue())
    assert answers == [{"id": "CLR-1", "answer": "改为 ra-ContentionResolutionTimer", "action": "answer", "by": ""},
                       {"id": "CLR-2", "answer": "", "action": "waive", "by": "王五"}]


# ---------- 一致性 / 歧义 / 复述 ----------

def _kinds(clar):
    return {(it["req_id"], it["kind"]): it for it in clar["items"]}


def test_consistency_checks():
    reqs = [
        _req("AR-1", expected=["SIB19 携带 ntn-NeighCellConfigList-r17，并按 tn-AreaIdList-r18 选择 TN 小区"]),
        _req("AR-2", trigger=["SS 下发 t-Service-r17 为 300"],
             explicit_configs=[{"name": "t-Service-r17", "value": "500", "source_text": ""}]),
        _req("AR-3", explicit_configs=[{"name": "t-Service-r17", "value": "600", "source_text": ""}]),
        _req("AR-4", title="NTN 小区Barred时 重选到其他小区", description="NTN 小区Barred时 重选到其他小区"),
        _req("AR-5", title="NTN 小区Barred时 重选到其他小区", description="NTN 小区Barred时 重选到其他小区"),
    ]
    k = _kinds(build_clarifications(reqs))
    assert not k[("AR-1", "release_mismatch")]["blocking"] and k[("AR-1", "release_mismatch")]["field"] == "tn-AreaIdList-r18"
    assert k[("AR-2", "text_config_conflict")]["blocking"]
    assert not k[("AR-2", "inconsistent_value")]["blocking"]
    assert ("AR-5", "duplicate") in k


def test_ambiguity_checks():
    reqs = [_req("AR-1", acceptance={"pass_fail": ["两种星历格式的结果无明显差异"]}, expected=["UE 正常注册"]),
            _req("AR-2", expected=["UE 结合 R 准则以及时间/位置启测机制完成重选"])]
    clar = build_clarifications(reqs, ambiguities=[
        {"req_id": "AR-2", "text": "完成重选", "readings": ["同频重选", "异频重选"], "question": "重选范围不明确"}])
    amb = [it for it in clar["items"] if it["kind"] == "ambiguity"]
    assert [(a["req_id"], a["blocking"]) for a in amb] == [("AR-1", True), ("AR-2", True)]  # “以及时”不是“及时”，“正常注册”不算含糊
    assert "读法1：同频重选" in amb[1]["question"]


def test_restatement_cards():
    spec = _spec([_req(explicit_configs=[{"name": "cellBarredNTN-r17", "value": ["barred", "notBarred"]}], trigger=[])], [])
    card = restatement_cards(spec)[0]
    assert card["parts"]["配置"] == ["cellBarredNTN-r17 = barred / notBarred"]
    assert card["gaps"] == ["触发"] and card["release"] == "R17" and not card["confirmed"]


def test_reapply_keeps_answers_across_rounds():
    def fresh():
        return [_req(explicit_configs=[{"name": "enhancedMeasurementLEO-r17", "value": "true", "source_text": ""}])]

    first = {"final_requirements": fresh()}
    first["clarifications"] = build_clarifications(first["final_requirements"])
    cid = next(it["id"] for it in first["clarifications"]["items"] if it["field"] == "enhancedMeasurementLEO-r17")
    C.apply_answers(first, [{"id": cid, "answer": "替换为 enhancedMeasurementNGSO-r17"}], confirmations={"AR-1": True})
    assert C.gate_status(first)["unconfirmed"] == ["AR-1"]  # 同一次提交里需求被改了，之前看到的复述作废
    C.apply_answers(first, [], confirmations={"AR-1": True})
    # 下一轮评审从原文重新生成需求：回答沿用，改动重新写回，需求没变的理解确认沿用
    second = {"final_requirements": fresh()}
    second["clarifications"] = build_clarifications(second["final_requirements"], previous=first["clarifications"]["items"])
    C.reapply(second, first)
    assert second["final_requirements"][0]["explicit_configs"][0]["name"] == "enhancedMeasurementNGSO-r17"
    assert C.gate_status(second)["unconfirmed"] == []


# ---------- 规范表插件 ----------

def test_spec_table_checker(tmp_path):
    (tmp_path / "nas.csv").write_text("spec,name,values,min,max,unit\nTS 24.501,5GMM cause,#3|#6|#7,,,\nTS 24.501,T3512,,0,31,min\n",
                                      encoding="utf-8")
    try:
        assert spec_checkers.load_tables(str(tmp_path)) == ["TS 24.501"]
        reqs = [_req(trigger=["网络拒绝，5GMM cause = #99"], explicit_configs=[{"name": "T3512", "value": "40"}])]
        clar = build_clarifications(copy.deepcopy(reqs))
        hits = [it for it in clar["items"] if "TS 24.501 核对" in it["raised_by"]]
        assert {it["field"] for it in hits} == {"5GMM cause", "T3512"} and all(it["blocking"] for it in hits)
        cov = {c["spec"]: c for c in spec_checkers.coverage()}
        assert cov["TS 24.501"]["entries"] == 2 and "未加载" in cov["TS 38.321"]["description"]
    finally:
        spec_checkers.load_tables(str(tmp_path / "none"))
    assert "未加载" in {c["spec"]: c for c in spec_checkers.coverage()}["TS 24.501"]["description"]
