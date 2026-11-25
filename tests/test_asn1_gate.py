"""IE 路径 ASN.1 核对、需求澄清闸门的回归用例。

用例取自 NR-NTN 设计稿在仪表信令校对时发现的问题（R17/R18 扩展挂错父结构、编造字段、“…”省略、
dBm 当 RSRP-Range、列表当 BIT STRING、评审发现了却照样输出）。"""
import re
from pathlib import Path

from core import asn1_paths as A
from core import ie_gate
from core.clarification import build_clarifications, owner_questions
from core.quality import finalize_pending
from core.tcd import patch_explicit_configs
from exec_cases import gate_exec_item

RRC = "RRCReconfiguration"


def _codes(res):
    return {i["code"] for i in res["issues"]}


# ---------- 路径核对 ----------

def test_valid_paths_pass():
    ok = [
        ("SIB1", "nonCriticalExtension.nonCriticalExtension.nonCriticalExtension.si-SchedulingInfo-v1700"
                 ".schedulingInfoList2-r17[0].sib-MappingInfo-r17[0].sibType-r17.type1-r17", "sibType19"),
        ("SIB4", "interFreqCarrierFreqList-v1720[0].smtc4list-r17[0].offset-r17", "3"),
        (RRC, "radioBearerConfig.drb-ToAddModList[0].pdcp-Config.discardTimerExt2-r17.setup", "ms2000"),
        (RRC, "measConfig.reportConfigToAddModList[0].reportConfig.reportConfigNR.reportType.eventTriggered.eventId"
              ".eventD1-r17.timeToTrigger-r17", "ms5120"),
        ("SIB19", "ntn-CovEnh-r18.rsrp-ThresholdMsg4HARQ-ACK-r18", "45"),
        ("SIB19", "ntn-CovEnh-r18.numberOfMsg4HARQ-ACK-Repetitions-r18", "'0111'B"),
        # 简写：nonCriticalExtension×5(→…)
        (RRC, "RRCReconfiguration.nonCriticalExtension×5(→RRCReconfiguration-v1700-IEs).otherConfig-v1700"
              ".propDelayDiffReportConfig-r17.setup.threshPropDelayDiff-r17", "ms1"),
    ]
    for msg, path, value in ok:
        res = A.validate_ie(msg, path, value)
        assert res["status"] == "ok", (path, res["issues"])


def test_extension_under_base_structure_is_relocated():
    res = A.validate_ie(RRC, "otherConfig.propDelayDiffReportConfig-r17.setup.threshPropDelayDiff-r17", "ms1")
    assert res["status"] == "error" and "WRONG_LOCATION" in _codes(res)
    assert res["suggestions"][0]["unique"]
    assert res["suggestions"][0]["display"].startswith(
        "nonCriticalExtension×5(→RRCReconfiguration-v1700-IEs).otherConfig-v1700.propDelayDiffReportConfig-r17")

    res = A.validate_ie(RRC, "radioBearerConfig.drb-ToAddModList[0].pdcp-Config.drb.discardTimerExt2-r17", "ms2000")
    assert res["suggestions"][0]["display"] == "radioBearerConfig.drb-ToAddModList[0].pdcp-Config.discardTimerExt2-r17"

    res = A.validate_ie("SIB4", "interFreqCarrierFreqList[0].smtc4list-r17[1]", "")
    assert res["suggestions"][0]["display"] == "interFreqCarrierFreqList-v1720[0].smtc4list-r17[1]"


def test_elided_and_free_text_paths_are_errors():
    assert "ELIDED_PATH" in _codes(A.validate_ie(RRC, "masterCellGroup.spCellConfig… tag-Config.tag-ToAddModList[0].timeAlignmentTimer", "ms5120"))
    assert "ELIDED_PATH" in _codes(A.validate_ie("UEAssistanceInformation", "…propagationDelayDifference-r17", "3"))
    assert "NOT_A_PATH" in _codes(A.validate_ie("SIB1", "si-SchedulingInfo / valueTag", "valueTag 加 1"))


def test_invented_field_is_rejected_not_guessed():
    res = A.validate_ie("SIB1", "servingCellConfigCommon.uplinkConfigCommon.initialUplinkBWP.rach-ConfigCommon"
                                ".ra-ContentionResolutionTimerExt-r18", "sf256")
    assert res["status"] == "error" and "UNKNOWN_FIELD" in _codes(res)
    assert not any(s.get("unique") for s in res["suggestions"])
    ie = {"path": "servingCellConfigCommon.uplinkConfigCommon.initialUplinkBWP.rach-ConfigCommon"
                  ".ra-ContentionResolutionTimerExt-r18", "value": "sf256"}
    verdict = ie_gate.check_ie("SIB1", ie)
    assert verdict["status"] == "error" and "fixed_from" not in ie  # 不能自动改成别的字段


def test_field_in_other_message():
    res = A.validate_ie("SIB1", "servingCellConfigCommon.uplinkConfigCommon.initialUplinkBWP.rach-ConfigCommon"
                                ".rsrp-ThresholdMsg4HARQ-ACK-r18", "对应 -115 dBm 的 RSRP-Range 取值")
    assert "WRONG_MESSAGE" in _codes(res)
    assert res["elsewhere"][0]["message"] == "SIB19-r17"


def test_value_checks():
    assert "BAD_ENUM" in _codes(A.validate_ie(
        "SIB1", "nonCriticalExtension×3.si-SchedulingInfo-v1700.schedulingInfoList2-r17[0].sib-MappingInfo-r17[0]"
                ".sibType-r17.type1-r17", "sibType19-v1700"))
    assert "UNIT_MISMATCH" in _codes(A.validate_ie("SIB19", "ntn-CovEnh-r18.rsrp-ThresholdMsg4HARQ-ACK-r18", "-115 dBm"))
    assert "OUT_OF_RANGE" in _codes(A.validate_ie("SIB19", "ntn-CovEnh-r18.rsrp-ThresholdMsg4HARQ-ACK-r18", "200"))
    assert "BAD_BITSTRING" in _codes(A.validate_ie("SIB19", "ntn-CovEnh-r18.numberOfMsg4HARQ-ACK-Repetitions-r18", "{n2, n4, n8}"))
    # 十六进制位串按长度核对；NAS / MAC CE 不在 38.331 里，不核对
    assert A.validate_ie("RRCRelease", "suspendConfig.fullI-RNTI", "0x0000000001")["status"] == "ok"
    assert ie_gate.check_ie("RegistrationReject", {"path": "5GMMCause", "value": "#22"})["status"] == "unchecked"


def test_missing_mandatory_in_new_list_entry():
    warns = A.missing_mandatory("SIB1", [
        "nonCriticalExtension×3.si-SchedulingInfo-v1700.schedulingInfoList2-r17[0].sib-MappingInfo-r17[0].sibType-r17.type1-r17"])
    text = " ".join(w["message"] for w in warns)
    assert "si-BroadcastStatus-r17" in text and "si-Periodicity-r17" in text


# ---------- IE 闸门 ----------

def test_gate_autofixes_only_certain_cases():
    msgs = [{"msg_id": "M1", "message": RRC, "direction": "DL", "ies": [
        {"path": "masterCellGroup.spCellConfig.reconfigurationWithSync.t304", "value": "ms2000"},
        {"path": "otherConfig.propDelayDiffReportConfig-r17", "value": "release"},
        {"path": "measConfig.reportConfigToAddModList[0].reportConfigNR.reportType.eventTriggered.eventId.eventD1-r17.timeToTrigger",
         "value": "ms5120"},
        {"path": "masterCellGroup.rlc-BearerToAddModList[0].rlc-Config.am.dl-AM-RLC.t-ReassemblyExt-r17", "value": "ms550"},
    ]}]
    rep = ie_gate.check_messages(msgs)
    ies = msgs[0]["ies"]
    assert ies[0]["asn1"]["status"] == "fixed"
    assert ies[0]["path"].startswith("nonCriticalExtension.masterCellGroup.")
    assert ies[1]["asn1"]["status"] == "fixed" and "otherConfig-v1700" in ies[1]["path"]
    assert ies[2]["asn1"]["status"] == "fixed" and ies[2]["path"].endswith("eventD1-r17.timeToTrigger-r17")
    # AM / UM 两处都有 t-ReassemblyExt-r17：按上下文选出来的不自动改，交给返工 / 人确认
    assert ies[3]["asn1"]["status"] == "error" and "dl-AM-RLC-v1700" in ies[3]["asn1"]["suggestions"][0]
    assert len(rep["fixed"]) == 3 and len(rep["errors"]) == 1


def test_gate_never_drops_a_version_suffix():
    # si-SchedulingInfo-v1700 改成老的 si-SchedulingInfo 等于换了一个版本的字段，不能自动改
    msgs = [{"msg_id": "M1", "message": "SIB1", "direction": "DL", "ies": [
        {"path": "si-SchedulingInfo-v1700 … sib-MappingInfo", "value": "含 SIB25"}]}]
    ie_gate.check_messages(msgs)
    ie = msgs[0]["ies"][0]
    assert ie["asn1"]["status"] == "error" and "fixed_from" not in ie
    assert ie_gate._renames_safe(["timeToTrigger → timeToTrigger-r17"])
    assert not ie_gate._renames_safe(["si-SchedulingInfo-v1700 → si-SchedulingInfo"])


def test_finalize_marks_cases_pending():
    tc = {"tc_id": "TC-1", "trace": {"req_ids": ["AR-1"]}, "open_points": [],
          "message_contents": [{"msg_id": "M1", "message": "SIB1", "ies": [
              {"path": "servingCellConfigCommon.uplinkConfigCommon.initialUplinkBWP.rach-ConfigCommon.ra-ContentionResolutionTimerExt-r18",
               "value": "sf256"}]}]}
    ie_gate.check_messages(tc["message_contents"])
    stats = finalize_pending([tc], {})
    assert stats["ie_invalid"] == 1 and tc["status"] == "pending_clarification"
    assert any("ra-ContentionResolutionTimerExt-r18" in x for x in tc["open_points"])


# ---------- 需求澄清 ----------

RAW_92429 = ("【AR 92429】DPC NTN中，在没有MSG4 HARQ反馈重复中需要应用扩展的定时器。\n"
             "1. 网络在NTN小区 SIB1 -> rach-ConfigCommon 中配置R18扩展竞争解决定时器（如 ra-ContentionResolutionTimerExt-r18 = sf128/sf256/sf512）")
RAW_106999 = "【AR 106999】1. 网络在 SIB1 中配置 rsrp-ThresholdMsg4HARQ-ACK-r18 (如 -115 dBm) 及 PUCCH重复次数集(n2/n4/n8)"
RAW_99182 = "【AR 99182】需求细化稿引用：RRCReconfiguration -> otherConfig -> propDelayDiffReportConfig-r17"


def _reqs():
    return [
        {"req_id": "AR-92429", "title": "扩展竞争解决定时器", "explicit_configs": []},
        {"req_id": "AR-106999", "title": "Msg4 HARQ-ACK 重复",
         "explicit_configs": [{"name": "rsrp-ThresholdMsg4HARQ-ACK-r18", "value": "-115 dBm", "target": "message",
                               "source_text": RAW_106999}]},
        {"req_id": "AR-99182", "title": "时延差上报", "explicit_configs": []},
    ]


def test_clarification_blocks_invented_field_and_wrong_unit():
    reqs = _reqs()
    clar = build_clarifications(reqs, raw_requirements=[RAW_92429, RAW_106999, RAW_99182])
    by = {}
    for it in clar["items"]:
        by.setdefault((it["req_id"], it["kind"]), []).append(it)
    unknown = by[("AR-92429", "unknown_field")][0]
    assert unknown["blocking"] and unknown["status"] == "open" and unknown["field"] == "ra-ContentionResolutionTimerExt-r18"
    # RSRP-Range 门限写成 dBm：38.331 规定门限实际值 = (IE 值 − 156) dBm，规范能定，换算成索引 41，不阻塞
    value = by[("AR-106999", "value_type")][0]
    assert not value["blocking"] and value["status"] == "resolved_by_spec" and "41" in value["suggestion"]
    assert by[("AR-106999", "wrong_message")][0]["status"] == "resolved_by_spec"  # 位置规范能定：在 SIB19
    assert by[("AR-99182", "wrong_location")][0]["status"] == "resolved_by_spec"
    assert set(clar["pending_req_ids"]) == {"AR-92429"}
    assert reqs[0]["clarification"]["status"] == "pending" and reqs[2]["clarification"]["status"] == "clear"
    # 换不了的类型错误（列表写成位图）仍然阻塞，且不会被“需求配置不丢”机制原样补进用例
    bad = [{"req_id": "AR-1", "title": "x", "explicit_configs": [
        {"name": "numberOfMsg4HARQ-ACK-Repetitions-r18", "value": "{n2, n4, n8}", "target": "message", "source_text": ""}]}]
    clar2 = build_clarifications(bad)
    assert clar2["pending_req_ids"] == ["AR-1"] and bad[0]["explicit_configs"][0].get("clarification")
    qs = owner_questions({"clarifications": clar2})
    assert qs and all(q["blocking"] and q["priority"] == "P0" for q in qs)


def test_owner_answer_resolves_item():
    first = build_clarifications(_reqs(), raw_requirements=[RAW_92429])
    item = next(it for it in first["items"] if it["kind"] == "unknown_field")
    answered = [{"req_id": item["req_id"], "question": item["question"], "answer": "改用 ra-ContentionResolutionTimer = sf64", "source": "用户"}]
    second = build_clarifications(_reqs(), raw_requirements=[RAW_92429], answered=answered)
    again = next(it for it in second["items"] if it["kind"] == "unknown_field")
    assert again["status"] == "resolved_by_owner" and "AR-92429" not in second["pending_req_ids"]
    # AI 自己给的答案不算澄清
    ai = [{**answered[0], "source": "一键模式采纳 AI 建议"}]
    third = build_clarifications(_reqs(), raw_requirements=[RAW_92429], answered=ai)
    assert "AR-92429" in third["pending_req_ids"]


def test_review_doubt_is_answered_by_spec_when_possible():
    reviews = {"spec": {"reviews": [{"req_id": "AR-107001", "issues": [
        "1. rach-LessHO-r18 下的字段名（细化稿写 cg-Config）和 TA 指示方式需按 TS 38.331 R18 核对"]}]}}
    clar = build_clarifications([{"req_id": "AR-107001", "title": "RACH-less HO"}], persona_reviews=reviews)
    doubt = next(it for it in clar["items"] if it["kind"] == "spec_doubt")
    assert "targetNTA-r18" in doubt["evidence"] or doubt["status"] == "open"


def test_pending_config_is_not_patched_into_testcase():
    tc = {"configuration": {"cells": [], "core": {}, "ue": {}, "other": {}}, "message_contents": [], "procedure": [],
          "parameter_variations": [], "open_points": []}
    cfg = [{"req_id": "AR-106999", "name": "rsrp-ThresholdMsg4HARQ-ACK-r18", "value": "-115 dBm", "target": "message",
            "source_text": RAW_106999, "clarification": "取值类型不符"}]
    res = patch_explicit_configs(tc, cfg)
    assert res[0]["status"] == "pending_clarification"
    assert "-115" not in str(tc["message_contents"]) and "-115" not in str(tc["configuration"])


def test_exec_case_of_pending_requirement_is_held():
    item = {"source_tc_id": "TC-9", "message_configs": [{"msg_id": "M1", "message": RRC, "ies": [
        {"path": "otherConfig.propDelayDiffReportConfig-r17.setup.threshPropDelayDiff-r17", "value": "ms1"}]}], "open_points": []}
    rep = gate_exec_item("protocol", item, {"trace": {"req_ids": ["AR-92429"]}}, {"AR-92429"})
    assert rep["fixed"] and "otherConfig-v1700" in item["message_configs"][0]["ies"][0]["path"]
    assert item["status"] == "pending_clarification" and item["blocked_by"]


def test_prompt_examples_are_valid_asn1():
    """内置提示词里的示例路径会被模型照着学，必须是正确的完整路径。"""
    text = (Path(__file__).resolve().parents[1] / "prompts" / "exec_case_protocol.txt").read_text(encoding="utf-8")
    paths = re.findall(r'"path": "([^"]*nonCriticalExtension[^"]*)"', text)
    assert paths
    for p in paths:
        assert "..." not in p and "…" not in p
        assert A.validate_ie(RRC, p, None)["status"] == "ok", p


def test_rsrp_dbm_threshold_converted_and_setup_added():
    msgs = [{"msg_id": "M1", "message": "SIB19", "direction": "DL", "ies": [
        {"path": "ntn-CovEnh-r18.rsrp-ThresholdMsg4HARQ-ACK-r18", "value": "对应 -115 dBm 的 RSRP-Range 取值"},
        {"path": "t-Service-r17", "value": "T0 + 30s"}]},
        {"msg_id": "M2", "message": "SIB1", "direction": "DL", "ies": [
            {"path": "sdt-ConfigCommon-r17.sdt-RSRP-Threshold-r17", "value": "-100 dBm"},
            {"path": "servingCellConfigCommon.uplinkConfigCommon.initialUplinkBWP.rach-ConfigCommon.ra-ContentionResolutionTimer",
             "value": "sf64"}]}]
    ie_gate.check_messages(msgs)
    a, b = msgs[0]["ies"]
    assert a["value"] == 41 and a["asn1"]["status"] == "fixed" and a["value_from"]
    assert b["asn1"]["status"] == "warning"  # 表达式不是具体整数
    c, d = msgs[1]["ies"]
    assert c["value"] == 56 and c["path"].startswith("nonCriticalExtension.nonCriticalExtension.nonCriticalExtension.")
    assert ".rach-ConfigCommon.setup.ra-ContentionResolutionTimer" in d["path"] and d["asn1"]["status"] == "fixed"


def test_bad_value_still_gets_path_fixed():
    msgs = [{"msg_id": "M1", "message": "SIB1", "direction": "DL", "ies": [
        {"path": "sdt-ConfigCommon-r17.sdt-RSRP-Threshold-r17", "value": 200}]}]
    ie_gate.check_messages(msgs)
    ie = msgs[0]["ies"][0]
    assert ie["asn1"]["status"] == "error" and ie["path"].startswith("nonCriticalExtension.") and ie["fixed_from"]


def test_unreferenced_message_is_reported():
    item = {"procedure": [{"step": 1, "msg_ref": "M1"}], "signaling_flow": [],
            "parameter_variations": [{"name": "x", "variants": [{"id": "v2", "msg_ref": "M3"}]}],
            "message_configs": [{"msg_id": "M1", "message": "SIB1"}, {"msg_id": "M2", "message": "SIB19"},
                                {"msg_id": "M3", "message": "SERVICE REJECT"}]}
    assert ie_gate.unreferenced_messages(item, "message_configs") == ["M2 SIB19"]
