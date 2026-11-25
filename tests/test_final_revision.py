"""终稿评审修订：意见落点、改写闸门（追溯锁定 / IE / 新增字段溯源 / 覆盖）、差异、采纳成新版本和撤销。

用假 LLM 离线跑，运行：python -m pytest -q tests/test_final_revision.py
"""
import asyncio
import copy
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("TESTFLOW_DATA_DIR", tempfile.mkdtemp(prefix="testflow-test-"))

import pytest  # noqa: E402

import core.llm as llm_runtime  # noqa: E402
from core import final_revision as FR  # noqa: E402
from core.events import EventLog  # noqa: E402
from core.tcd import normalize_tcd  # noqa: E402
from utils.llm_client import LLMResponse  # noqa: E402

llm_runtime._BACKOFF_BASE = 0

RRC = "RRCReconfiguration"
GOOD_PATH = "radioBearerConfig.drb-ToAddModList[0].pdcp-Config.discardTimerExt2-r17.setup"


def _req(rid, title, configs=None):
    return {"req_id": rid, "title": title, "priority": "P1", "expected": ["..."],
            "acceptance": {"pass_fail": ["成功率 99%"]}, "explicit_configs": configs or []}


def _row(rid, req, env="PROTOCOL_ANALYZER"):
    return {"row_id": rid, "req_id": req, "objective_id": "TO-001", "technique": "normal", "scenario": f"{rid} 场景",
            "test_purpose": {"with": "UE 已注册", "when": "下发配置", "then": "UE 应用配置"},
            "key_configuration": {}, "pass_criteria": ["UE 回复 RRCReconfigurationComplete"],
            "test_environment": {"primary": env}}


def _tc(tc_id, row, req, title):
    return normalize_tcd({
        "tc_id": tc_id, "title": title, "technique": "normal",
        "test_purpose": {"with": "UE 已注册", "when": "SS 下发 RRCReconfiguration", "then": "UE 回复 RRCReconfigurationComplete"},
        "test_environment": {"primary": "PROTOCOL_ANALYZER"},
        "initial_conditions": {"system_simulator": ["NR Cell 1 激活"], "ue": ["RRC_CONNECTED"], "preamble": []},
        "configuration": {"cells": [{"cell_id": "Cell1", "band": "n78"}], "core": {"T3346": "12min"} if req == "REQ-001" else {}, "ue": {}},
        "message_contents": [{"msg_id": "M1", "message": RRC, "direction": "DL", "ies": [{"path": GOOD_PATH, "value": "ms2000"}]}],
        "procedure": [
            {"step": 1, "actor": "SS", "action": "SEND", "direction": "DL", "layer": "RRC", "message": RRC, "msg_ref": "M1", "expected": "下发"},
            {"step": 2, "actor": "UE", "action": "SEND", "direction": "UL", "layer": "RRC", "message": "RRCReconfigurationComplete",
             "expected": "UE 回复 RRCReconfigurationComplete", "verdict": True},
        ],
        "pass_fail": ["UE 回复 RRCReconfigurationComplete"],
        "trace": {"req_ids": [req], "source_refs": [row]},
    })


def _record():
    reqs = [_req("REQ-001", "T3346 退避", [{"name": "T3346", "value": "12min", "target": "core", "source_text": "T3346=12min"}]),
            _req("REQ-002", "PDCP discardTimerExt2")]
    rows = [_row("ROW-001", "REQ-001"), _row("ROW-002", "REQ-001"), _row("ROW-003", "REQ-002")]
    tcs = [_tc("TC-001", "ROW-001", "REQ-001", "注册被拒后 T3346 退避"),
           _tc("TC-002", "ROW-002", "REQ-001", "注册被拒后 T3346 退避（重复）"),
           _tc("TC-003", "ROW-003", "REQ-002", "PDCP discardTimerExt2 配置")]
    return {"record_id": "rec00001", "requirement_spec": {"final_requirements": reqs},
            "test_design_spec": {"objectives": [{"objective_id": "TO-001"}], "integrated_matrix": rows},
            "test_case_spec": {"testcases": tcs}}


COMMENTS = """[TC-001] 补一步：T3346 超时后 UE 重新发起注册
[TC-002] 和 TC-001 重复，删掉
[TC-003] 也删掉
TC-003：小区配置里加上 fooBarTimer，消息里配 measConfig.inventedField-r17
补充 REQ-002 的边界场景：discardTimerExt2 取最大值
T3346 改成 6min"""


class FakeLLM:
    enabled = True

    def __init__(self):
        self.revise_calls = 0
        self.feedback = []

    @staticmethod
    def _ok(obj):
        return LLMResponse(text=json.dumps(obj, ensure_ascii=False), finish_reason="stop", usage={})

    def chat(self, messages, temperature=0.2, max_tokens=None, json_mode=False):
        system, user = messages[0]["content"], messages[1]["content"]
        if "评审负责人" in system and "修订已经定稿" not in system:
            return self._ok({"comments": [
                {"comment_id": "RC-01", "understanding": "TC-001 缺少 T3346 超时后的重新注册", "decision": "revise",
                 "targets": ["TC-001"], "instruction": "在 procedure 末尾加 WAIT T3346 超时和 UE 重新发起 RegistrationRequest 的判定步骤"},
                {"comment_id": "RC-02", "decision": "remove", "targets": ["TC-002"], "reason": "与 TC-001 重复"},
                {"comment_id": "RC-03", "decision": "reject", "reason": "TC-003 是 REQ-002 唯一的用例，不能删"},
                {"comment_id": "RC-04", "decision": "revise", "targets": ["TC-003"], "instruction": "加 fooBarTimer 和 inventedField-r17"},
                {"comment_id": "RC-05", "decision": "add", "add": [{"req_id": "REQ-002", "scenario": "discardTimerExt2 取最大值",
                                                                    "technique": "boundary", "base_row": "ROW-003"}]},
                {"comment_id": "RC-06", "decision": "revise", "targets": ["TC-001"], "instruction": "T3346 改 6min"},
            ]})
        if "修订已经定稿" in system:
            self.revise_calls += 1
            items = json.loads(user.split("items: ", 1)[1].split("\nrequirements: ", 1)[0])
            ctx = user.split("\ncontext: ", 1)[1]
            if "上一次修订结果没有通过核对" in ctx:
                self.feedback.append(ctx[:200])
            out, notes = [], []
            for it in items:
                if it["new"]:
                    tc = _tc(it["tc_id"], "ROW-X", "REQ-002", "discardTimerExt2 取最大值")
                    tc["message_contents"][0]["ies"][0]["value"] = "ms2000"
                    out.append(tc)
                    continue
                tc = copy.deepcopy(it["current"])
                ids = [c["comment_id"] for c in it["comments"]]
                if "RC-01" in ids:
                    tc["procedure"].append({"step": 3, "actor": "SS", "action": "WAIT", "expected": "T3346 超时"})
                    tc["procedure"].append({"step": 4, "actor": "UE", "action": "SEND", "direction": "UL", "layer": "NAS",
                                            "message": "RegistrationRequest", "expected": "UE 重新发起注册", "verdict": True})
                    tc["test_environment"] = {"primary": "REAL_NETWORK"}  # 改环境：应被锁回
                    tc["trace"] = {"req_ids": ["REQ-001", "REQ-002"], "source_refs": ["ROW-001"]}  # 改追溯：应被锁回
                    tc["configuration"]["core"]["T3346"] = "6min"  # 与需求冲突：应被标出
                    notes.append({"tc_id": tc["tc_id"], "comment_ids": ["RC-01"], "field": "procedure", "what": "加两步"})
                if "RC-04" in ids:
                    tc["configuration"]["cells"][0]["fooBarTimer"] = 5
                    tc["configuration"]["cells"][0]["dl_arfcn"] = 632628  # 意见没提、需求没有、其他用例也没有 → 无出处
                    tc["message_contents"][0]["ies"].append({"path": "measConfig.inventedField-r17", "value": "1"})
                out.append(tc)
            return self._ok({"testcases": out, "change_notes": notes})
        raise AssertionError(f"unexpected prompt: {system[:40]}")


def _proposal(record, llm=None):
    llm = llm or FakeLLM()
    shared = {"llm_client": llm, "warnings": []}
    from nodes import _requirement_view
    return asyncio.run(FR.build_proposal(shared, record, FR.parse_comments(COMMENTS), _requirement_view, EventLog())), llm


def test_parse_comments_targets():
    cs = FR.parse_comments("1. [TC-003] 加等待步骤\n【ROW-002】重复\nREQ-001：缺异常\n整体再看下定时器")
    assert [c["target"] for c in cs] == ["TC-003", "ROW-002", "REQ-001", ""]
    assert cs[0]["text"] == "加等待步骤" and cs[0]["comment_id"] == "RC-01"


def test_proposal_gates_and_diff():
    record = _record()
    prop, llm = _proposal(record)
    by_c = {c["comment_id"]: c for c in prop["comments"]}
    assert by_c["RC-06"]["decision"] == "revise"
    ch = {(c["op"], c["tc_id"]): c for c in prop["changes"]}

    # RC-01：加步骤；环境 / 追溯被锁回；T3346 被需求值拉回并标冲突
    up = ch[("update", "TC-001")]
    assert set(up["comment_ids"]) == {"RC-01", "RC-06"}
    after = up["after"]
    assert after["test_environment"]["primary"] == "PROTOCOL_ANALYZER"
    assert after["trace"] == {"req_ids": ["REQ-001"], "source_refs": ["ROW-001"]}
    assert len(up["gate"]["locked"]) == 2
    assert up["gate"]["conflicts"] and up["status"] == "warn"
    fields = [d["field"] for d in up["diff"]]
    assert any(f.startswith("测试步骤 #3") for f in fields) and any(f.startswith("测试步骤 #4") for f in fields)
    assert not any(f.startswith("测试步骤 #1") or f.startswith("测试步骤 #2") for f in fields)  # 插步骤不会让前面的步骤都算改了

    # RC-04：编造的 IE 被闸门拦下（重试一次仍错 → blocked），无出处的新增配置被列出
    bad = ch[("update", "TC-003")]
    assert bad["status"] == "blocked" and bad["gate"]["ie_errors"]
    assert "配置 小区.dl_arfcn" in bad["gate"]["unbacked"]
    assert "配置 小区.fooBarTimer" not in bad["gate"]["unbacked"]  # 评审意见里点名了，有出处
    assert bad["after"]["status"] == "pending_clarification"
    assert llm.feedback, "IE 错误应带着错误回灌让模型再改一次"

    # 删除：TC-002 可以删（REQ-001 还有 TC-001）；不采纳的意见不产生修改，理由留着
    assert ch[("remove", "TC-002")]["status"] == "ok"
    assert by_c["RC-03"]["decision"] == "reject" and by_c["RC-03"]["reason"] and not by_c["RC-03"]["change_ids"]

    # 新增：挂到 REQ-002，新测试点和新编号
    add = next(c for c in prop["changes"] if c["op"] == "add")
    assert add["tc_id"] == "TC-004" and add["row"]["row_id"] == "ROW-004" and add["row"]["req_id"] == "REQ-002"
    assert add["after"]["trace"] == {"req_ids": ["REQ-002"], "source_refs": ["ROW-004"]}
    assert add["row"]["technique"] == "boundary"


def test_remove_that_loses_coverage_is_blocked():
    record = _record()
    llm = FakeLLM()
    orig = llm.chat

    def no_add(messages, **kw):
        resp = orig(messages, **kw)
        if "修订已经定稿" not in messages[0]["content"]:
            data = json.loads(resp.text)
            data["comments"] = [c for c in data["comments"] if c["decision"] not in ("add", "reject")]
            data["comments"].append({"comment_id": "RC-03", "decision": "remove", "targets": ["ROW-003"]})
            return FakeLLM._ok(data)
        return resp
    llm.chat = no_add
    prop, _ = _proposal(record, llm)
    rm = next(c for c in prop["changes"] if c["op"] == "remove" and c["tc_id"] == "TC-003")
    assert rm["status"] == "blocked" and rm["gate"]["lost_coverage"] == ["REQ-002"]
    with pytest.raises(FR.RevisionError):
        FR.apply_changes(record, prop, [rm["change_id"]])


def test_requirement_level_comment_not_applied():
    record = _record()
    llm = FakeLLM()
    orig = llm.chat

    def plan_req_change(messages, **kw):
        resp = orig(messages, **kw)
        if "修订已经定稿" not in messages[0]["content"]:
            data = json.loads(resp.text)
            data["comments"][5] = {"comment_id": "RC-06", "decision": "requirement_change", "reason": "T3346 是需求写明的取值，请在需求澄清里改"}
            data["comments"][4] = {"comment_id": "RC-05", "decision": "add", "add": [{"req_id": "REQ-999", "scenario": "x"}]}
            return FakeLLM._ok(data)
        return resp
    llm.chat = plan_req_change
    prop, _ = _proposal(record, llm)
    by_c = {c["comment_id"]: c for c in prop["comments"]}
    assert by_c["RC-06"]["decision"] == "requirement_change" and not by_c["RC-06"]["change_ids"]
    assert by_c["RC-05"]["decision"] == "requirement_change"  # 挂不到已定稿需求的新增 → 回到需求澄清
    assert not any(c["op"] == "add" for c in prop["changes"])


def test_accept_creates_version_and_revert(monkeypatch):
    import main

    record = _record()
    main._write_design_history_record(record)
    fake = FakeLLM()
    monkeypatch.setattr(main, "LLMClient", lambda: fake)
    payload = main.StageGenerateRequest(history_record_id="rec00001", review_comments=COMMENTS, reviewer="王工")
    res = asyncio.run(main._stage_revise(payload, EventLog()))
    prop = res["revision_proposal"]
    assert prop["version"] == 1
    pick = [c["change_id"] for c in prop["changes"] if c["status"] in ("ok", "warn") and c["tc_id"] != "TC-003"]
    out = main.final_review_accept(main.FinalReviewAcceptRequest(record_id="rec00001", proposal_id=prop["proposal_id"], accepted=pick))
    assert out["version"] == 2
    ids = [tc["tc_id"] for tc in out["test_case_spec"]["testcases"]]
    assert ids == ["TC-001", "TC-003", "TC-004"]
    assert [r["row_id"] for r in out["test_design_spec"]["integrated_matrix"]] == ["ROW-001", "ROW-003", "ROW-004"]
    saved = main._load_design_history_record("rec00001")
    assert saved["final_revisions"][0]["version"] == 2 and saved["status"] == "final_revised"
    assert saved["final_revisions"][0]["comments"][0]["applied"]
    doc = main._render_design_document_html(saved)
    assert "评审修订记录" in doc and "王工" in doc
    # 同一份提案不能再采纳一次
    with pytest.raises(main.HTTPException):
        main.final_review_accept(main.FinalReviewAcceptRequest(record_id="rec00001", proposal_id=prop["proposal_id"], accepted=pick))
    # 撤销回 v1
    back = main.final_review_revert(main.FinalReviewRevertRequest(record_id="rec00001"))
    assert back["version"] == 1
    assert [tc["tc_id"] for tc in back["test_case_spec"]["testcases"]] == ["TC-001", "TC-002", "TC-003"]


def test_stale_proposal_rejected():
    record = _record()
    prop, _ = _proposal(record)
    record["test_case_spec"]["testcases"][0]["title"] = "别处改过"
    with pytest.raises(FR.RevisionError):
        FR.apply_changes(record, prop, [prop["changes"][0]["change_id"]])


def test_revise_requires_final_draft():
    import main

    main._write_design_history_record({"record_id": "rec00002", "test_design_spec": {"integrated_matrix": []}})
    with pytest.raises(main.HTTPException) as e:
        asyncio.run(main.stage_start("revise", main.StageGenerateRequest(history_record_id="rec00002", review_comments="x")))
    assert e.value.status_code == 409
