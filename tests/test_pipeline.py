"""离线测试：用假 LLM 跑完整流水线，覆盖自修复、截断拆批、补漏、需求配置补入、专家评审、定向返工和草稿投影，
以及 LLM 客户端的参数兼容、限流重试、任务事件流（断线续传）。

运行：python -m pytest -q
"""
import asyncio
import json
import os
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("TESTFLOW_DATA_DIR", tempfile.mkdtemp(prefix="testflow-test-"))

import core.llm as llm_runtime  # noqa: E402
from core.events import EventLog  # noqa: E402
from core.llm import generate_json, split_prompt  # noqa: E402
from core.quality import criterion_covered, repair_design_rows, review_testcases  # noqa: E402
from core.tcd import message_layer, normalize_tcd, patch_explicit_configs, project, purpose_text  # noqa: E402
from flow import create_exec_case_flow, create_requirement_analysis_flow, create_test_case_flow, create_test_design_flow  # noqa: E402
from nodes import bind_tcds_to_rows  # noqa: E402
from utils import llm_client  # noqa: E402
from utils.llm_client import LLMClient, LLMHTTPError, LLMResponse  # noqa: E402
from utils.req_configs import config_status, normalize_explicit_configs  # noqa: E402

llm_runtime._BACKOFF_BASE = 0  # 测试里不真的等退避

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
        self.review_calls = 0
        self.feedback_seen = ""

    def chat(self, messages, temperature=0.2, max_tokens=None, json_mode=False):
        system, user = messages[0]["content"], messages[1]["content"]
        self.calls.append((system[:40], len(messages)))
        if "同行评审" in system:
            self.review_calls += 1
            reviews = []
            for tc in json.loads(user.split("testcases: ", 1)[1].split("\nrequirements: ", 1)[0]):
                row = tc["matrix_row"]["row_id"]
                issues = []
                if row == "ROW-002":
                    issues = [{"severity": "major", "field": "procedure", "problem": "没有等待 T3346 超时的步骤", "suggestion": "补 WAIT 步骤"}]
                elif row == "ROW-003":
                    issues = [{"severity": "minor", "field": "references", "problem": "可补充条款号", "suggestion": ""}]
                reviews.append({"tc_id": tc["tc_id"], "verdict": "revise" if issues else "pass", "issues": issues})
            return self._ok({"reviews": reviews})
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
            if "上一次生成的用例有以下问题" in user:
                self.feedback_seen = user
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
    assert llm.review_calls == 1, "专家评审只在首轮做一次"
    assert "专家评审：[procedure] 没有等待 T3346 超时的步骤" in llm.feedback_seen, "评审的严重问题应进入返工反馈"
    assert "ROW-003" not in llm.feedback_seen.split("请针对这些矩阵行重新生成并逐条改正")[1], "没有严重问题的测试点不返工"
    assert tcs[2]["review_notes"] == ["[references] 可补充条款号"], "一般意见留在用例里"
    assert "10s 内完成" in tcs[2]["pass_fail"]
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
    ams_cfg = {rc["name"]: rc["status"] for rc in ams["requirement_configs"]}
    assert set(ams_cfg.values()) <= {"applied", "patched"} and ams["core_config"].get("T3346") == "12min"
    art = ex["bundles"]["artemis"]["cases"][0]["task"]
    assert "10s 内完成" in art["expected_result"] and "99%" in art["expected_result"], "实网用例改写时丢掉的数值门限要补回"
    assert ex["bundles"]["amarisoft"]["version"] == 4 and ex["bundles"]["protocol"]["version"] == 6


def test_no_llm_still_produces_everything():
    class Off:
        enabled = False

    shared = {"input_requirements": [REQ_TEXT], "llm_client": Off(), "warnings": [], "trace": [],
              "requirement_spec": {"final_requirements": PARSED}}
    _run(create_test_design_flow(), shared)
    design = shared["test_design_spec"]
    assert {r["req_id"] for r in design["integrated_matrix"]} == {"REQ-001", "REQ-002"}, "没配 LLM 时按规则给出设计骨架"
    assert design["integrated_matrix"][0]["key_configuration"]["T3346"] == "12min"
    shared["test_design_spec"] = {"objectives": [{"objective_id": "TO-001"}], "integrated_matrix": [
        {"row_id": "ROW-001", "req_id": "REQ-001", "objective_id": "TO-001", "technique": "abnormal",
         "scenario": "注册被拒", "test_purpose": {"when": "收到 #22", "then": "启动 T3346"},
         "key_configuration": {"band": "n78", "T3346": "12min"}, "pass_criteria": ["不重发"],
         "test_environment": {"primary": "PROTOCOL_ANALYZER"}}]}
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


def test_requirement_config_status():
    item = {"configuration": {"cells": [{"cell_id": "Cell1", "ssb_arfcn": 620000, "band": "n78"}], "core": {"T3346": "12min"}},
            "message_contents": [{"msg_id": "M1", "ies": [{"path": "a.5GMMCause", "value": "#22"}]}],
            "procedure": [{"step": 12, "action": "WAIT", "params": {"duration": "30s"}}]}
    fields = ["configuration", "message_contents", "procedure"]
    st = lambda n, v: config_status({"name": n, "value": v}, item, fields)["status"]  # noqa: E731
    assert st("T3346", "12min") == "applied" and st("5GMM cause", "#22") == "applied"
    assert st("ssb_arfcn", 632628) == "conflict", "同名参数取值不同要认出来"
    assert st("T3324", 12) == "missing", "步骤号 12、别的参数里的 12min 不能算 T3324=12 已落地"
    assert st("n311", "5") == "missing", "一位数取值只认同名参数"
    reqs = normalize_explicit_configs({"req_id": "R", "explicit_configs": [{"name": "bandwidth", "value": ["20MHz", "100MHz"]}]})
    assert [c["value"] for c in reqs] == ["20MHz", "100MHz"], "数组取值拆成多条"


def test_patch_explicit_configs_conflict_and_sweep():
    tc = normalize_tcd({"title": "t", "procedure": [{"action": "SEND", "message": "RegistrationReject", "direction": "DL",
                                                      "expected": "x", "verdict": True}],
                        "configuration": {"cells": [{"ssb_arfcn": 620000, "bandwidth": "20MHz"}], "core": {}}})
    configs = [{"name": "ssb_arfcn", "value": 632628, "target": "cell"}, {"name": "T3346", "value": "12min", "target": "core"},
               {"name": "bandwidth", "value": "20MHz", "target": "cell"}, {"name": "bandwidth", "value": "100MHz", "target": "cell"}]
    status = {(r["name"], str(r["value"])): r["status"] for r in patch_explicit_configs(tc, configs)}
    assert status == {("ssb_arfcn", "632628"): "conflict", ("T3346", "12min"): "patched",
                      ("bandwidth", "20MHz"): "applied", ("bandwidth", "100MHz"): "patched"}
    cell = tc["configuration"]["cells"][0]
    assert cell["ssb_arfcn"] == 620000 and cell["ssb_arfcn（需求值）"] == 632628, "冲突时不覆盖原值，需求值另存"
    assert tc["parameter_variations"][0]["values"] == ["20MHz", "100MHz"], "同名多值按扫描补入"
    assert any("需求配置冲突" in x for x in tc["open_points"])
    n_open = len(tc["open_points"])
    again = {(r["name"], str(r["value"])): r["status"] for r in patch_explicit_configs(tc, configs)}
    assert again == status and len(tc["open_points"]) == n_open, "重复核对结论不变、不重复补"
    res = review_testcases([dict(tc, tc_id="TC-001", trace={"req_ids": [], "source_refs": ["ROW-1"]})], [],
                           [{"row_id": "ROW-1", "pass_criteria": ["时延 ≤ 150ms", "流程成功"]}])
    assert res["criteria_added"] == 1, "矩阵行的数值门限要进 pass_fail"


def test_quality_helpers():
    assert criterion_covered("成功率 99%", ["注册成功率不低于 99 %"]) and not criterion_covered("成功率 99%", ["成功率 95%"])
    assert not criterion_covered("T3346 运行期间 0 次 RegistrationRequest", ["T3346 超时后重发"])
    rows = [{"row_id": "ROW-1", "req_id": "REQ-002", "technique": "abnormal", "key_configuration": {}, "pass_criteria": ["x"]},
            {"row_id": "ROW-2", "req_id": "REQ-002", "technique": "normal", "key_configuration": {}, "pass_criteria": ["10s 内完成会话建立"]}]
    assert repair_design_rows(rows, PARSED)["metrics"] == 1
    assert rows[1]["pass_criteria"] == ["10s 内完成会话建立", "成功率 99%"] and rows[0]["pass_criteria"] == ["x"], \
        "已被带上的门限不重复补；缺的只补到正常流程行"
    assert message_layer("RRCReconfigurationComplete") == "RRC" and message_layer("RegistrationRequest") == "NAS"
    assert message_layer("INVITE") == "IMS" and message_layer("183 Session Progress") == "IMS" and message_layer("HARQ-ACK") == ""


def test_bind_tcds_to_rows_handles_bad_refs():
    rows = [{"row_id": "ROW-001", "req_id": "REQ-001", "objective_id": "TO-001", "technique": "timer",
             "test_environment": {"primary": "AMARISOFT"}},
            {"row_id": "ROW-002", "req_id": "REQ-002", "objective_id": "TO-002", "technique": "normal",
             "test_environment": {"primary": "REAL_NETWORK"}}]
    step = [{"action": "CHECK", "expected": "ok", "verdict": True}]
    raw = [{"title": "b", "procedure": step, "trace": {"req_ids": ["REQ-002"], "source_refs": ["第二行"]},
            "test_environment": {"primary": "AMARISOFT"}, "technique": "abnormal"},
           {"title": "a", "procedure": step, "trace": {"req_ids": [], "source_refs": []}}]
    out = bind_tcds_to_rows(raw, rows, {"REQ-001": {"priority": "P0"}, "REQ-002": {}})
    by_title = {t["title"]: t for t in out}
    assert by_title["b"]["trace"]["source_refs"] == ["ROW-002"] and by_title["a"]["trace"]["source_refs"] == ["ROW-001"]
    assert by_title["b"]["test_environment"]["primary"] == "REAL_NETWORK" and by_title["b"]["technique"] == "normal", \
        "环境和测试技术以矩阵行为准"
    assert by_title["a"]["priority"] == "P0" and by_title["a"]["objective_id"] == "TO-001" and by_title["a"]["trace"]["req_ids"] == ["REQ-001"]


def test_llm_client_adapts_to_unsupported_params(monkeypatch):
    client = LLMClient({"api_base": "http://x/v1", "api_key": "k", "model": "m", "max_tokens": 4096})
    sent = []

    def fake_post(payload):
        sent.append(dict(payload))
        if "max_tokens" in payload:
            raise LLMHTTPError(400, "Unsupported parameter: 'max_tokens'. Use 'max_completion_tokens' instead.")
        if "temperature" in payload:
            raise LLMHTTPError(400, "Unsupported value: 'temperature' does not support 0.2 with this model.")
        if "response_format" in payload:
            raise LLMHTTPError(400, "response_format is not supported")
        return {"choices": [{"message": {"content": [{"type": "text", "text": "{}"}]}, "finish_reason": "stop"}]}

    monkeypatch.setattr(client, "_post", fake_post)
    llm_client._COMPAT.clear()
    assert client.chat([{"role": "user", "content": "hi"}], json_mode=True).text == "{}"
    assert len(sent) == 4 and sent[-1] == {"model": "m", "messages": [{"role": "user", "content": "hi"}], "max_completion_tokens": 4096}
    client.chat([{"role": "user", "content": "hi"}], json_mode=True)
    assert len(sent) == 5, "记住接口的习惯后不再先失败一次"

    def always_400(payload):
        raise LLMHTTPError(400, "context length exceeded")

    llm_client._COMPAT.clear()
    monkeypatch.setattr(client, "_post", always_400)
    try:
        client.chat([{"role": "user", "content": "hi"}], json_mode=True)
        raise AssertionError("应抛出异常")
    except LLMHTTPError:
        pass
    assert not llm_client._COMPAT, "去掉参数后仍失败，说明不是参数问题，不应记成不支持"


def test_generate_json_retry_policy():
    class Flaky:
        enabled = True

        def __init__(self, errors):
            self.errors, self.calls = list(errors), 0

        def chat(self, messages, **kwargs):
            self.calls += 1
            if self.errors:
                raise self.errors.pop(0)
            return LLMResponse('{"ok": true}', "stop")

    schema = {"type": "object", "required": ["ok"]}
    kw = dict(template_name="req_parse.txt", variables={k: "" for k in (
        "glossary_json", "doc_meta_json", "text_chunk", "rag_context", "review_feedback", "product_profile_json")}, schema=schema)
    flaky = Flaky([LLMHTTPError(429, "rate limited"), RuntimeError("LLM 请求失败: timed out")])
    shared = {"llm_client": flaky}
    assert generate_json(shared=shared, warn_tag="T", **kw) == {"ok": True} and flaky.calls == 3
    assert shared["llm_usage"]["failures"] == 2
    bad_key = Flaky([LLMHTTPError(401, "invalid api key")] * 3)
    try:
        generate_json(shared={"llm_client": bad_key}, warn_tag="T", **kw)
        raise AssertionError("应抛出异常")
    except RuntimeError as exc:
        assert "API Key" in str(exc)
    assert bad_key.calls == 1, "鉴权失败重试没有意义，应立即报错"


def test_event_log_resume_and_threads():
    async def scenario():
        log = EventLog().bind()
        log.emit("job_started", {})
        got = []

        async def reader(cursor):
            async for seq, ev in log.stream(cursor, keepalive=0.05):
                got.append((seq, ev["type"] if ev else None))

        task = asyncio.create_task(reader(0))
        await asyncio.sleep(0.12)  # 空闲时应收到心跳
        threading.Thread(target=lambda: (log.emit("node_running", {"node": "X"}), log.emit("completed", {}))).start()
        await asyncio.wait_for(task, 2)
        events = [g for g in got if g[1]]
        assert events == [(1, "job_started"), (2, "node_running"), (3, "completed")], events
        assert any(g[1] is None for g in got), "空闲时要发心跳"
        got.clear()
        await asyncio.wait_for(reader(2), 2)  # 断线后带 Last-Event-ID=2 重连：只补发之后的事件
        assert got == [(3, "completed")]

    asyncio.run(scenario())


def _sse_events(client, url, headers=None):
    out = []
    with client.stream("GET", url, headers=headers or {}) as resp:
        assert resp.status_code == 200
        seq = None
        for line in resp.iter_lines():
            if line.startswith("id: "):
                seq = int(line[4:])
            elif line.startswith("data: "):
                out.append((seq, json.loads(line[6:])))
                seq = None
    return out


def test_auto_stage_job_stream():
    """没配 LLM 也能一键跑完四个阶段；事件流不重复，断线后能按 Last-Event-ID 续上。"""
    from fastapi.testclient import TestClient
    import main

    with TestClient(main.app) as client:
        job = client.post("/api/stage/auto/start", json={"requirement_input": [REQ_TEXT], "expert_review": False}).json()
        events = _sse_events(client, f"/api/stage/{job['job_id']}/stream")
        types = [e["type"] for _, e in events]
        assert types[0] == "state" and types[-1] == "completed", types
        assert types.count("job_started") == 1 and types.count("stage_result") == 4, "每个事件只发一次"
        assert [e["payload"]["stage"] for _, e in events if e["type"] == "stage_progress"] == ["requirements", "design", "testcases", "exec_cases"]
        assert "node_running" in types
        result = events[-1][1]["payload"]["result"]
        assert result["test_case_spec"]["testcases"] and result["executable_cases"]["bundles"]
        last_seq = events[-1][0]
        resumed = _sse_events(client, f"/api/stage/{job['job_id']}/stream", {"Last-Event-ID": str(last_seq - 1)})
        assert [e["type"] for _, e in resumed] == ["completed"]
        st = client.get(f"/api/stage/{job['job_id']}/state").json()
        assert st["status"] == "completed"


def test_llm_settings_max_tokens():
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    saved = client.post("/api/settings/llm", json={"api_base": "http://127.0.0.1:1/v1", "model": "m", "max_tokens": 8192}).json()
    assert saved["max_tokens"] == 8192
    kept = client.post("/api/settings/llm", json={"api_base": "http://127.0.0.1:1/v1", "model": "m"}).json()
    assert kept["max_tokens"] == 8192, "表单没带这一项时沿用旧值"
    assert client.post("/api/settings/llm", json={"api_base": "", "model": "", "max_tokens": 0}).json()["max_tokens"] == 0


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
