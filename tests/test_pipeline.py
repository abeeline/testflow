"""离线测试：用假 LLM 跑完整流水线，覆盖自修复、截断拆批、补漏、需求配置补入、定向返工和草稿投影。

运行：python -m pytest -q
"""
import asyncio
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("TESTFLOW_DATA_DIR", tempfile.mkdtemp(prefix="testflow-test-"))

from core.llm import split_prompt  # noqa: E402
from core.tcd import normalize_tcd, project, purpose_text  # noqa: E402
from flow import create_exec_case_flow, create_requirement_analysis_flow, create_test_case_flow, create_test_design_flow  # noqa: E402
from utils.llm_client import LLMResponse  # noqa: E402

REQ_TEXT = ("UE 在 NR SA 小区 n78（ssb_arfcn=632628）注册被拒，cause #22，T3346=12min，T3346 运行期间不得再次发起注册。\n"
            "注册成功后 10s 内完成 PDU 会话建立，成功率 99%。")


def _req(rid, title, configs, metrics):
    return {"req_id": rid, "title": title, "source": {"type": "PRD", "doc_id": "USER_INPUT"}, "feature": "NAS",
            "rat_scope": ["5G"], "preconditions": [], "expected": ["..."], "acceptance": {"pass_fail": metrics},
            "observability": {"signals": [], "logs": [], "counters": []}, "priority": "P1", "explicit_configs": configs}


PARSED = [
    _req("REQ-001", "注册拒绝 #22 与 T3346", [
        {"name": "ssb_arfcn", "value": 632628, "target": "cell", "source_text": "ssb_arfcn=632628"},
        {"name": "T3346", "value": "12min", "target": "core", "source_text": "T3346=12min"},
        {"name": "5GMM cause", "value": "#22", "target": "message", "source_text": "cause #22"},
    ], ["T3346 运行期间 0 次 RegistrationRequest"]),
    _req("REQ-002", "PDU 会话建立时延", [], ["10s 内完成", "成功率 99%"]),
]


class FakeLLM:
    """按 system 提示词识别是哪个 Agent，返回预设答案；记录调用以便断言。"""

    enabled = True

    def __init__(self):
        self.calls = []
        self.tcd_calls = 0
        self.design_calls = 0

    def chat(self, messages, temperature=0.2, max_tokens=None, json_mode=False):
        system, user = messages[0]["content"], messages[1]["content"]
        self.calls.append((system[:40], len(messages)))
        if "requirements analyst" in system:
            return self._ok(PARSED)
        if "Role:" in system:
            return self._ok({"reviews": [{"req_id": "REQ-001", "issues": ["x"], "rewrite_suggestion": "", "scores": {},
                                          "must_observe": [], "open_questions": [
                                              {"question": "T3346 是否由网络下发", "priority": "P2", "needs_user": False,
                                               "ai_answer": "是", "basis": "TS 24.501"}]}]})
        if "Arbiter" in system:
            stripped = [dict(r, explicit_configs=[]) for r in PARSED]  # 故意丢掉显式配置，验证补回
            return self._ok({"final_requirements": stripped, "conflicts": [], "questions_to_ask": [], "assumptions": []})
        if "一致性测试的设计方法" in system:
            self.design_calls += 1
            if self.design_calls == 1:
                return LLMResponse("这不是 JSON", "stop")  # 触发自修复
            return self._ok({
                "objectives": [{"objective_id": "TO-001", "linked_reqs": ["REQ-001"], "goal": "拒绝处理", "success_criteria": ["x"],
                                "evidence": [], "priority": "P1"},
                               {"objective_id": "TO-002", "linked_reqs": ["REQ-002"], "goal": "会话时延", "success_criteria": ["x"],
                                "evidence": [], "priority": "P1"}],
                "coverage_matrices": [],
                "integrated_matrix": [
                    {"row_id": "ROW-001", "req_id": "REQ-001", "objective_id": "TO-001", "technique": "abnormal",
                     "scenario": "注册被拒 #22", "test_purpose": {"with": "RRC_IDLE", "when": "收到 #22", "then": "启动 T3346"},
                     "key_configuration": {"RAT": "NR_SA", "band": "n78"}, "pass_criteria": ["不重发注册"],
                     "test_environment": {"primary": "PROTOCOL_ANALYZER"}},
                    {"row_id": "ROW-002", "req_id": "REQ-001", "objective_id": "TO-001", "technique": "timer",
                     "scenario": "T3346 超时后重注册", "key_configuration": {"RAT": "NR_SA"}, "pass_criteria": ["重发注册"],
                     "test_environment": {"primary": "AMARISOFT"}},
                ],
                "design_notes": [], "de_scoped": []})
        if "只为这些缺口补充" in system:
            return self._ok({"integrated_matrix": [
                {"row_id": "ROW-003", "req_id": "REQ-002", "objective_id": "TO-002", "technique": "performance",
                 "scenario": "会话建立时延", "key_configuration": {"RAT": "NR_SA"}, "pass_criteria": ["10s 内完成"],
                 "test_environment": {"primary": "REAL_NETWORK"}}]})
        if "Main behaviour" in system:
            self.tcd_calls += 1
            rows = json.loads(user.split("integrated_matrix: ", 1)[1].split("\nobjectives: ", 1)[0])
            if len(rows) > 1:
                return LLMResponse('{"testcases": [{"title": "被截断', "length")
            row = rows[0]
            tc = {
                "title": row["scenario"], "technique": row["technique"],
                "test_purpose": {"with": "RRC_IDLE", "when": "触发", "then": "检查"},
                "test_environment": row["test_environment"],
                "initial_conditions": {"ue": ["已开机"]},
                "configuration": {"cells": [{"cell_id": "Cell1", "band": "n78"}], "core": {}},
                "message_contents": [{"msg_id": "M1", "message": "RegistrationReject", "direction": "DL",
                                      "ies": [{"path": "5GMMCause", "value": "#22"}]}],
                "procedure": [
                    {"step": 1, "actor": "UE", "action": "SEND", "direction": "UL", "message": "RegistrationRequest", "expected": "发起注册"},
                    {"step": 2, "actor": "SS", "action": "SEND", "direction": "DL", "message": "RegistrationReject", "msg_ref": "M1",
                     "expected": "UE 启动 T3346", "verdict": True},
                ],
                "pass_fail": row["pass_criteria"],
                "trace": {"req_ids": [row["req_id"]], "source_refs": [row["row_id"]]},
            }
            if row["row_id"] == "ROW-001" and "上一次生成的用例有以下问题" not in user:
                tc["test_purpose"] = {"when": "", "then": ""}  # 第一次故意不合格，验证只返工这一行
            return self._ok({"testcases": [tc]})
        if "Amarisoft" in system:
            tcs = json.loads(user.split("testcases: ", 1)[1].split("\ndraft_cases: ", 1)[0])
            # 故意只给部分字段，验证草稿补齐
            return self._ok({"cases": [{"source_tc_id": t["tc_id"], "cell_config": {"band": "n78"}, "procedure": [{"step": 1, "action": "START_CELL"}]} for t in tcs]})
        if "协议" in system:
            raise RuntimeError("模拟接口故障")  # 验证草稿兜底
        if "Artemis" in system or "AT Agent" in system:
            tcs = json.loads(user.split("testcases: ", 1)[1].split("\ndraft_cases: ", 1)[0])
            return self._ok({"cases": [{"source_tc_id": t["tc_id"], "title": t["title"], "goal": "按步骤执行", "expected_result": "通过"} for t in tcs]})
        raise AssertionError(f"未识别的 Agent: {system[:80]}")

    @staticmethod
    def _ok(data):
        return LLMResponse(json.dumps(data, ensure_ascii=False), "stop", {"prompt_tokens": 10, "completion_tokens": 5})


def _run(flow, shared):
    asyncio.run(flow.run_async(shared))
    return shared


def test_split_prompt():
    sys_part, user_part = split_prompt("[System]\nA\nB\n[User]\nC {x}")
    assert sys_part == "A\nB" and user_part == "C {x}"
    assert split_prompt("no markers") == ("", "no markers")


def test_full_pipeline_offline():
    llm = FakeLLM()
    shared = {"input_requirements": [REQ_TEXT], "llm_client": llm, "warnings": [], "trace": [],
              "product_profile": {"selected": {"form_factor": ["智能手机"]}},
              "test_environments": {"selected_ids": ["AMARISOFT", "PROTOCOL_ANALYZER", "REAL_NETWORK"]}}
    _run(create_requirement_analysis_flow(), shared)
    finals = shared["requirement_spec"]["final_requirements"]
    assert finals[0]["explicit_configs"], "综合定稿丢掉的显式配置应按 req_id 补回"

    _run(create_test_design_flow(), shared)
    design = shared["test_design_spec"]
    rows = design["integrated_matrix"]
    assert llm.design_calls == 2, "第一次输出不是 JSON，应带错误回灌自修复一次"
    assert {r["req_id"] for r in rows} == {"REQ-001", "REQ-002"}, "REQ-002 应由补漏调用补上"
    row1 = next(r for r in rows if r["row_id"] == "ROW-001")
    assert row1["key_configuration"].get("T3346") == "12min", "需求写明的配置应确定性补进矩阵行"
    assert "T3346 运行期间 0 次 RegistrationRequest" in row1["pass_criteria"]
    assert design["generation_meta"]["gap_filled_rows"] == 1

    _run(create_test_case_flow(), shared)
    tcs = shared["test_case_spec"]["testcases"]
    assert [t["tc_id"] for t in tcs] == ["TC-001", "TC-002", "TC-003"], "按矩阵行顺序统一编号，不撞号"
    assert all(t["test_purpose"]["when"] for t in tcs), "不合格用例应被定向返工"
    assert shared["testcase_retry_count"] == 1
    tc1 = tcs[0]
    assert tc1["configuration"]["cells"][0].get("ssb_arfcn") == 632628, "需求写明的小区配置应补入 TCD"
    assert tc1["configuration"]["core"].get("T3346") == "12min"
    assert any(r["status"] == "patched" for r in tc1["requirement_configs"])
    assert tc1["steps"] and tc1["preconditions"], "保留兼容字段"
    assert "ensure that" in purpose_text(tc1)
    usage = shared["llm_usage"]
    assert usage["repairs"] >= 1 and usage["calls"] > 0

    _run(create_exec_case_flow(), shared)
    ex = shared["executable_cases"]
    assert ex["summary"]["protocol"] == 1 and ex["summary"]["amarisoft"] == 1 and ex["summary"]["artemis"] == 1
    ams = ex["bundles"]["amarisoft"]["cases"][0]
    assert ams["test_purpose"]["then"] and ams["expected_signaling"], "LLM 漏掉的字段应由 TCD 草稿补齐"
    assert ams["cell_config"].get("band") == "n78"
    prt = ex["bundles"]["protocol"]["items"][0]
    assert prt["message_configs"] and prt["signaling_flow"], "LLM 失败时协议用例用草稿兜底"
    statuses = {rc["name"]: rc["status"] for rc in prt["requirement_configs"]}
    assert statuses.get("T3346") == "applied" and statuses.get("ssb_arfcn") == "applied"
    assert ex["bundles"]["amarisoft"]["version"] == 3 and ex["bundles"]["protocol"]["version"] == 4


def test_no_llm_still_produces_everything():
    class Off:
        enabled = False

    shared = {"input_requirements": [REQ_TEXT], "llm_client": Off(), "warnings": [], "trace": [],
              "requirement_spec": {"final_requirements": PARSED},
              "test_design_spec": {"objectives": [{"objective_id": "TO-001"}], "integrated_matrix": [
                  {"row_id": "ROW-001", "req_id": "REQ-001", "objective_id": "TO-001", "technique": "abnormal",
                   "scenario": "注册被拒", "test_purpose": {"when": "收到 #22", "then": "启动 T3346"},
                   "key_configuration": {"band": "n78", "T3346": "12min"}, "pass_criteria": ["不重发"],
                   "test_environment": {"primary": "PROTOCOL_ANALYZER"}}]}}
    _run(create_test_case_flow(), shared)
    tc = shared["test_case_spec"]["testcases"][0]
    assert tc["configuration"]["cells"][0]["band"] == "n78" and tc["configuration"]["core"]["T3346"] == "12min"
    _run(create_exec_case_flow(), shared)
    item = shared["executable_cases"]["bundles"]["protocol"]["items"][0]
    assert item["cell_config"]["band"] == "n78"


def test_legacy_testcase_projects():
    legacy = {"tc_id": "TC-9", "title": "旧用例", "steps": [{"action": "TRIGGER_REGISTRATION", "params": {"mode": "NR_SA"}}],
              "pass_fail": ["2s 内注册"], "trace": {"req_ids": ["REQ-1"], "source_refs": ["ROW-1"]}}
    tc = normalize_tcd(legacy)
    assert tc["procedure"][0]["action"] == "TRIGGER_REGISTRATION"
    assert project("artemis", legacy)["goal"].startswith("旧用例")
    assert project("protocol", legacy)["source_tc_id"] == "TC-9"


def test_api_smoke():
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    assert client.get("/api/settings/flow-visualization").status_code == 200
    prompts = client.get("/api/settings/prompts").json()
    assert "test_case_tcd.txt" in json.dumps(prompts, ensure_ascii=False)
    r = client.post("/api/export/testcases.xlsx", json={"test_case_spec": {"testcases": [normalize_tcd({
        "title": "x", "procedure": [{"action": "SEND", "message": "RRCSetupRequest", "direction": "UL", "expected": "ok", "verdict": True}],
        "message_contents": [{"msg_id": "M1", "message": "RRCSetup", "ies": [{"path": "a.b", "value": 1}]}]})]}})
    assert r.status_code == 200 and len(r.content) > 1000
    assert client.post("/api/stage/auto/start", json={"requirement_input": []}).status_code == 400
