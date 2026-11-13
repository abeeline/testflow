"""需求清单相关：表格导入、两级分组、长清单分批、测试技术别名、配置行上限。

运行：python -m pytest -q
"""
import asyncio
import base64
import io
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("TESTFLOW_DATA_DIR", tempfile.mkdtemp(prefix="testflow-test-"))

import openpyxl  # noqa: E402

from core.grouping import attach_suites, requirement_group, restore_groups, suite_tree  # noqa: E402
from core.tcd import normalize_technique  # noqa: E402
from flow import create_exec_case_flow, create_requirement_analysis_flow, create_test_case_flow, create_test_design_flow  # noqa: E402
from utils.llm_client import LLMResponse  # noqa: E402
from utils.req_configs import extract_config_lines  # noqa: E402
from utils.req_import import parse_requirement_sheet  # noqa: E402


def _run(flow, shared):
    asyncio.run(flow.run_async(shared))


def _sheet_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["SR描述", "SR", "AR", "描述", "需求细化/拆解", "模块", "Release"])
    ws.append(["NTN 选择、\n驻留处理", 38428, 99157, "NTN 小区 Barred 时重选到其他小区", "配置 cellBarredNTN-r17 = barred", "AS", "R17"])
    ws.append([None, None, 99158, "读取 SIB19", "ntn-UlSyncValidityDuration-r17 = s240", "AS", "R17"])
    ws.append(["MSG4 HARQ 反馈重复", 409172, 106992, "Msg4 HARQ-ACK 重复", "PUCCH 重复 4 次", "PHY", "R18"])
    ws.append(["双连接", 409158, 106992, "解析 tn-AreaIdList", "SIB25 给出 TN 区域", "AS", "R18"])
    ws.append([None, None, None, None, None, None, None])
    ws.merge_cells("A2:A3")
    ws.merge_cells("B2:B3")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_import_requirement_sheet():
    out = parse_requirement_sheet("ar.xlsx", _sheet_bytes())
    assert [m["req_id"] for m in out["meta"]] == ["AR-99157", "AR-99158", "AR-106992", "AR-106992-SR409158"], \
        "需求编号沿用表格编号，重复的编号带上级编号区分"
    assert any("106992" in w and "重复" in w for w in out["warnings"])
    assert out["meta"][1]["group"][0] == "SR 38428 NTN 选择、驻留处理", "合并单元格的上级需求沿用到下面各行"
    assert out["meta"][1]["group"][1] == "AR 99158 读取 SIB19"
    assert [g["count"] for g in out["groups"]] == [2, 1, 1]
    text = out["requirements"][0]
    assert text.startswith("【AR 99157｜SR 38428") and "模块 AS" in text and "cellBarredNTN-r17 = barred" in text

    csv_out = parse_requirement_sheet("r.csv", "需求编号,需求描述\nR-1,开机注册\nR-2,关机去注册\n".encode("utf-8"))
    assert [m["req_id"] for m in csv_out["meta"]] == ["R-1", "R-2"] and len(csv_out["meta"][0]["group"]) == 1

    try:
        parse_requirement_sheet("x.csv", "a,b\n1,2\n".encode())
        raise AssertionError("没有描述列应报错")
    except ValueError as exc:
        assert "描述" in str(exc)


def test_grouping_helpers():
    reqs = [{"req_id": "AR-1", "title": "读取 SIB19", "group": ["SR 1 驻留", "AR 1 读取 SIB19"]},
            {"req_id": "AR-2", "title": "切换", "group": ["SR 2 切换"]},
            {"req_id": "REQ-003", "title": "注册", "feature": "NAS"},
            {"req_id": "REQ-004", "title": "默认", "feature": "MODEM_SYSTEM"}]
    assert requirement_group(reqs[0]) == ["SR 1 驻留", "AR 1 读取 SIB19"]
    assert requirement_group(reqs[1]) == ["SR 2 切换", "AR-2 切换"], "只有一级时二级用需求自己"
    assert requirement_group(reqs[2]) == ["NAS", "REQ-003 注册"], "没有分组时一级取 feature"
    assert requirement_group(reqs[3])[0] == "未分组"

    tcs = [{"tc_id": "TC-001", "trace": {"req_ids": ["AR-1"]}}, {"tc_id": "TC-002", "trace": {"req_ids": ["AR-1"]}},
           {"tc_id": "TC-003", "trace": {"req_ids": ["AR-2"]}}, {"tc_id": "TC-004", "trace": {"req_ids": ["none"]}}]
    attach_suites(tcs, {r["req_id"]: r for r in reqs})
    tree = suite_tree(tcs, id_key="tc_id")
    assert [(g["name"], g["count"]) for g in tree] == [("SR 1 驻留", 2), ("SR 2 切换", 1), ("未分组", 1)]
    assert tree[0]["children"][0]["case_ids"] == ["TC-001", "TC-002"]

    rewritten = [{"req_id": "AR-1", "title": "改写后"}, {"req_id": "AR-2", "group": ["保留"]}]
    assert restore_groups(rewritten, reqs) == 1
    assert rewritten[0]["group"] == ["SR 1 驻留", "AR 1 读取 SIB19"] and rewritten[1]["group"] == ["保留"]


def test_normalize_technique():
    assert normalize_technique("Combinational") == ("capability", "")
    assert normalize_technique("negative") == ("abnormal", "")
    assert normalize_technique("边界值") == ("boundary", "")
    assert normalize_technique("") == ("normal", "")
    assert normalize_technique("mobility") == ("mobility", "")
    assert normalize_technique("fuzzing") == ("normal", "fuzzing"), "认不出的按 normal 处理，并把原值带出来告警"


def test_config_line_cap_is_per_requirement():
    big = "\n".join(f"T3{i:03d}=ms{i}0" for i in range(100, 220))
    lines = extract_config_lines([big, "q-RxLevMin = -62dBm"])
    assert any(ln["text"] == "q-RxLevMin = -62dBm" and ln["req_no"] == 2 for ln in lines), \
        "前一条需求的配置行再多，也不能挤掉后面需求的"
    assert sum(1 for ln in lines if ln["req_no"] == 1) == 80


class BatchLLM:
    """每个节点只回答提示词里出现的那几条需求，目标和矩阵行每批都从 001 编号（故意撞号）。"""

    enabled = True

    def __init__(self):
        self.sizes = {}

    @staticmethod
    def _ids(text):
        return list(dict.fromkeys(re.findall(r'"req_id": "([^"]+)"', text)))

    def chat(self, messages, temperature=0.2, max_tokens=None, json_mode=False):
        system, user = messages[0]["content"], messages[1]["content"]

        def ok(data):
            return LLMResponse(json.dumps(data, ensure_ascii=False), "stop", {})

        if "requirements analyst" in system:
            seeds = json.loads(user.split("requirement_text_chunk: ", 1)[1].split("\nrag_context: ", 1)[0])
            self.sizes.setdefault("parse", []).append(len(seeds))
            return ok([{k: v for k, v in s.items() if k != "group"} for s in seeds])  # 模型把 group 弄丢了
        if "Role:" in system:
            ids = self._ids(user.split("requirements: ", 1)[1].split("\nreturn_schema: ", 1)[0])
            self.sizes.setdefault("review", []).append(len(ids))
            return ok({"reviews": [{"req_id": i, "issues": [], "rewrite_suggestion": "", "scores": {}, "must_observe": [],
                                    "open_questions": []} for i in ids]})
        if "Arbiter" in system:
            body = user.split("requirements: ", 1)[1]
            reqs = json.loads(body.split("\nreviews_spec: ", 1)[0])
            reviewed = self._ids(body.split("\nreviews_spec: ", 1)[1].split("\nreturn_schema: ", 1)[0])
            assert set(reviewed) <= {r["req_id"] for r in reqs}, "每批只带本批需求的评审意见"
            self.sizes.setdefault("arbiter", []).append(len(reqs))
            return ok({"final_requirements": [{k: v for k, v in r.items() if k != "group"} for r in reqs], "conflicts": [],
                       "questions_to_ask": ["统一问题"], "assumptions": [f"假设-{reqs[0]['req_id']}"]})
        if "一致性测试的设计方法" in system:
            reqs = json.loads(user.split("final_requirements: ", 1)[1].split("\nconstraints: ", 1)[0])
            self.sizes.setdefault("design", []).append(len(reqs))
            return ok({"objectives": [{"objective_id": f"TO-{i:03d}", "linked_reqs": [r["req_id"]], "goal": r["title"][:20]}
                                      for i, r in enumerate(reqs, 1)],
                       "coverage_matrices": [{"matrix_id": "CM-001", "dimensions": []}],
                       "integrated_matrix": [{"row_id": f"ROW-{i:03d}", "req_id": r["req_id"], "objective_id": f"TO-{i:03d}",
                                              "technique": "combinational", "scenario": f"{r['req_id']} 正常流程",
                                              "key_configuration": {}, "pass_criteria": ["成功"],
                                              "test_environment": {"primary": "AMARISOFT"}} for i, r in enumerate(reqs, 1)],
                       "design_notes": ["通用说明"], "de_scoped": []})
        raise RuntimeError("本测试不模拟这个节点")


def test_long_requirement_list_runs_in_batches(monkeypatch):
    monkeypatch.setenv("TESTFLOW_REQ_BATCH_SIZE", "2")
    texts = [f"需求 {i}：UE 在 n25{i} 上完成注册" for i in range(1, 6)]
    meta = [{"req_id": f"AR-{100 + i}", "group": [f"SR {1 + i // 3}", f"AR {100 + i}"]} for i in range(1, 6)]
    meta[4]["req_id"] = "AR-101"  # 清单里编号重复
    llm = BatchLLM()
    shared = {"input_requirements": texts, "requirement_meta": meta, "llm_client": llm, "warnings": [], "trace": [],
              "test_environments": {"selected_ids": ["AMARISOFT", "PROTOCOL_ANALYZER"]}}
    _run(create_requirement_analysis_flow(), shared)
    finals = shared["requirement_spec"]["final_requirements"]
    ids = [r["req_id"] for r in finals]
    assert ids == ["AR-101", "AR-102", "AR-103", "AR-104", "AR-101-2"], "编号沿用导入的编号，重复的加后缀"
    assert any("重复" in w for w in shared["warnings"])
    assert all(r.get("group") for r in finals), "模型丢掉的分组按 req_id 补回"
    assert sorted(llm.sizes["parse"]) == [1, 2, 2] and sorted(llm.sizes["arbiter"]) == [1, 2, 2] and sorted(llm.sizes["review"]) == [1] * 3 + [2] * 6
    assert shared["requirement_spec"]["questions_to_ask"] == ["统一问题"], "各批相同的条目合并时去重"
    assert len(shared["requirement_spec"]["assumptions"]) == 3

    _run(create_test_design_flow(), shared)
    design = shared["test_design_spec"]
    assert sorted(llm.sizes["design"]) == [1, 2, 2], "各批并行，调用先后不固定"
    obj_ids = [o["objective_id"] for o in design["objectives"]]
    row_ids = [r["row_id"] for r in design["integrated_matrix"]]
    assert len(set(obj_ids)) == 5 and len(set(row_ids)) == 5, "各批撞号的目标和矩阵行合并后编号唯一"
    by_obj = {o["objective_id"]: o for o in design["objectives"]}
    assert all(r["req_id"] in by_obj[r["objective_id"]]["linked_reqs"] for r in design["integrated_matrix"]), \
        "目标改号后矩阵行仍指向本需求的目标"
    assert {r["technique"] for r in design["integrated_matrix"]} == {"capability"}, "combinational 归到 capability"
    assert design["design_notes"] == ["通用说明"]

    class Off:
        enabled = False

    shared["llm_client"] = Off()  # 用例和可执行用例走规则兜底，只看分组
    _run(create_test_case_flow(), shared)
    tcs = shared["test_case_spec"]["testcases"]
    assert [t["suite"] for t in tcs][0] == {"level1": "SR 1", "level2": "AR 101"}
    _run(create_exec_case_flow(), shared)
    ex = shared["executable_cases"]
    bundle = ex["bundles"]["amarisoft"]
    assert [(g["name"], g["count"]) for g in bundle["suites"]] == [("SR 1", 2), ("SR 2", 3)]
    assert bundle["cases"][0]["suite"]["level2"] == "AR 101"
    assert bundle["suites"][0]["children"][0]["case_ids"] == [bundle["cases"][0]["case_id"]]
    assert ex["traceability"][-1]["suite"] == {"level1": "SR 2", "level2": "AR 105"}


def test_import_api_and_grouped_export():
    from fastapi.testclient import TestClient
    import main
    from core.tcd import normalize_tcd

    client = TestClient(main.app)
    r = client.post("/api/requirements/import", json={"filename": "ar.xlsx",
                                                      "content_base64": base64.b64encode(_sheet_bytes()).decode()})
    assert r.status_code == 200 and len(r.json()["requirements"]) == 4
    assert client.post("/api/requirements/import", json={"filename": "a.xlsx", "content_base64": "AAAA"}).status_code == 400

    reqs = [{"req_id": "AR-1", "title": "读取 SIB19", "group": ["SR 1 驻留", "AR 1 读取 SIB19"]},
            {"req_id": "AR-2", "title": "切换", "group": ["SR 2 切换", "AR 2 切换"]}]
    tcs = [normalize_tcd({"tc_id": f"TC-00{i}", "title": f"用例{i}", "trace": {"req_ids": [rid], "source_refs": []},
                          "procedure": [{"action": "SEND", "message": "SIB19", "direction": "DL", "expected": "ok", "verdict": True}]})
           for i, rid in ((1, "AR-1"), (2, "AR-1"), (3, "AR-2"))]
    r = client.post("/api/export/testcases.xlsx", json={"requirement_spec": {"final_requirements": reqs},
                                                         "test_case_spec": {"testcases": tcs}})
    assert r.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    cases = list(wb["测试用例"].iter_rows(values_only=True))
    assert cases[0][:4] == ("一级模块", "二级模块", "用例编号", "测试点") and cases[3][:2] == ("SR 2 切换", "AR 2 切换")
    groups = list(wb["用例分组"].iter_rows(values_only=True))
    assert groups[1][:4] == ("SR 1 驻留", 2, "AR 1 读取 SIB19", 2) and groups[2][2:4] == ("AR 2 切换", 1)
    doc = main._render_design_document_html({"requirement_spec": {"final_requirements": reqs}, "test_case_spec": {"testcases": tcs},
                                             "test_design_spec": {"integrated_matrix": [{"row_id": "ROW-001", "req_id": "AR-1"}]}})
    assert "用例分组" in doc and "SR 1 驻留" in doc


def test_requirement_config_is_not_forced_into_a_wrong_message():
    from core.tcd import normalize_tcd, patch_explicit_configs, to_protocol
    from exec_cases import apply_requirement_configs

    def tc():
        return normalize_tcd({
            "tc_id": "TC-001", "title": "非激活态周期 RNA 更新", "trace": {"req_ids": ["AR-1"], "source_refs": ["ROW-1"]},
            "configuration": {"ue": {"T3540": "20s"}},
            "message_contents": [{"msg_id": "M1", "message": "RRCRelease", "direction": "DL", "ies": [{"path": "suspendConfig.t380", "value": "min5"}]},
                                 {"msg_id": "M2", "message": "UECapabilityInformation", "direction": "UL", "ies": []}],
            "procedure": [{"actor": "SS", "action": "SEND", "message": "RRCRelease", "direction": "DL", "msg_ref": "M1"},
                          {"actor": "TESTER", "action": "INJECT_LOCATION", "params": {"distance": "9.5 km"}},
                          {"actor": "SS", "action": "CHECK", "expected": "120s 内不重选", "verdict": True},
                          {"actor": "TESTER", "action": "INJECT_LOCATION", "params": {"distance": "10.5 km"}},
                          {"actor": "UE", "action": "SEND", "message": "RRCResumeRequest", "direction": "UL", "expected": "RNA 更新", "verdict": True}]})

    named = {"req_id": "AR-1", "name": "inactiveStateNTN-r17", "value": "supported", "target": "message",
             "source_text": "UE 在 UECapabilityInformation 中上报 inactiveStateNTN-r17 = supported"}
    orphan = {"req_id": "AR-1", "name": "fooBar-r17", "value": "enabled", "target": "message", "source_text": "fooBar-r17 = enabled"}

    case = tc()
    res = {r["name"]: r for r in patch_explicit_configs(case, [named, orphan])}
    by_id = {m["msg_id"]: m for m in case["message_contents"]}
    assert [ie["path"] for ie in by_id["M2"]["ies"]] == ["inactiveStateNTN-r17"], "补进原文点名的那条消息"
    assert len(by_id["M1"]["ies"]) == 1 and len(by_id) == 2, "不动其他消息，也不新建没有消息名的占位消息"
    assert "找不到它所属的消息" in res["fooBar-r17"]["note"] and any("fooBar-r17" in x for x in case["open_points"])

    item = to_protocol(tc())
    assert [p["action"] for p in item["procedure"]] == ["SEND", "INJECT_LOCATION", "CHECK", "INJECT_LOCATION", "SEND"], \
        "协议用例保留完整的有序步骤，包括非消息动作"
    assert [f["step"] for f in item["signaling_flow"]] == [1, 5] and item["ue_config"] == {"T3540": "20s"}
    apply_requirement_configs("protocol", item, [named, orphan, {"req_id": "AR-1", "name": "T3517", "value": "27s", "target": "ue", "source_text": "T3517 = 27s"}])
    status = {r["name"]: r["status"] for r in item["requirement_configs"]}
    assert status == {"inactiveStateNTN-r17": "patched", "fooBar-r17": "missing", "T3517": "patched"}
    msgs = {m["msg_id"]: m for m in item["message_configs"]}
    assert len(msgs["M1"]["ies"]) == 1, "UE 能力字段不能补进下行 RRCRelease"
    assert item["ue_config"]["T3517"] == "27s" and any("fooBar-r17" in x for x in item["open_points"])


def test_long_source_line_is_not_truncated():
    line = "ephemerisInfo-r17 = positionVelocity-r17，" + "说明" * 200 + "，epochTime-r17 = sfn0"
    lines = extract_config_lines([line])
    assert lines and lines[0]["text"] == line


def test_variants_with_own_expectations_reach_the_executable_cases():
    from core.tcd import normalize_tcd, to_amarisoft, to_protocol

    variants = [{"id": "V1", "value": "duration=1", "preconditions": "SMTC 窗口 1 ms", "expected": "不触发切换时判 INCONCLUSIVE"},
                {"id": "V2", "value": "duration=5", "preconditions": "SMTC 窗口 5 ms", "expected": "上报 A3"}]
    tc = normalize_tcd({
        "tc_id": "TC-001", "title": "SMTC 窗口扫描", "trace": {"req_ids": ["AR-1"], "source_refs": ["ROW-1"]},
        "procedure": [{"actor": "SS", "action": "CHECK", "expected": "按分支判定", "verdict": True}],
        "parameter_variations": [{"name": "smtc duration", "values": ["duration=1", "duration=5"], "purpose": "各分支预期不同", "variants": variants},
                                 {"name": "带宽", "values": ["5 MHz", "10 MHz"], "purpose": "同一预期"}]})
    ama, pro = to_amarisoft(tc)["key_parameters"], to_protocol(tc)["parameter_variations"]
    assert ama[0]["variants"] == variants and pro[0]["variants"] == variants, "每个取值自己的前置和预期要带到执行用例"
    assert "variants" not in ama[1] and "variants" not in pro[1]


def _design_record():
    reqs = [{"req_id": "AR-1", "title": "小区禁止时重选", "priority": "P1", "group": ["SR 10 选网", "AR 1 小区禁止时重选"]},
            {"req_id": "AR-2", "title": "定时器处理", "priority": "P0", "group": ["SR 10 选网", "AR 2 定时器处理"]},
            {"req_id": "AR-3", "title": "位置上报", "priority": "P2", "group": ["SR 20 位置", "AR 3 位置上报"]}]
    env = {"primary": "AMARISOFT", "primary_label": "Amarisoft模拟基站"}
    rows = [{"row_id": "ROW-1-1", "req_id": "AR-1", "objective_id": "TO-1", "technique": "normal", "scenario": "重选到邻区", "test_environment": env,
             "test_purpose": {"with": "A", "when": "B", "then": "C"}, "pass_criteria": ["PRACH 次数为 0"]},
            {"row_id": "ROW-1-2", "req_id": "AR-1", "objective_id": "TO-1", "technique": "negative", "scenario": "没有可用邻区</script>", "test_environment": env},
            {"row_id": "ROW-2-1", "req_id": "AR-2", "objective_id": "TO-2", "technique": "normal", "scenario": "定时器正常启动", "test_environment": env}]
    return {"title": "选网测试设计", "requirement_spec": {"final_requirements": reqs},
            "test_design_spec": {"integrated_matrix": rows, "objectives": [{"objective_id": "TO-1", "goal": "验证禁止小区处理"}]}}


def test_design_map_shows_structure_and_gaps():
    from core.design_map import build_design_map, render_design_map_html

    record = _design_record()
    data = build_design_map(record)
    assert [(m["name"], [r["id"] for r in m["requirements"]]) for m in data["modules"]] == [("SR 10 选网", ["AR-1", "AR-2"]), ("SR 20 位置", ["AR-3"])]
    ar1 = data["modules"][0]["requirements"][0]
    assert ar1["techniques"] == {"normal": 1, "abnormal": 1} and ar1["goal"] == "验证禁止小区处理" and not ar1["flags"]
    assert {(g["req_id"], g["kind"]) for g in data["gaps"]} == {("AR-2", "normal_only"), ("AR-3", "no_point")}, \
        "高优先级只有正常流程、需求没有测试点，都要作为评审关注点列出来"
    assert data["stats"]["points"] == 3 and not data["has_cases"]

    record["test_case_spec"] = {"testcases": [
        {"tc_id": "TC-001", "title": "重选", "trace": {"req_ids": ["AR-1"], "source_refs": ["ROW-1-1"]}},
        {"tc_id": "TC-002", "title": "补充", "trace": {"req_ids": ["AR-2"], "source_refs": ["ROW-9-9"]}}]}
    record["executable_cases"] = {"traceability": [{"tc_id": "TC-001", "exec_case_ids": ["AMS-001"]}]}
    data = build_design_map(record)
    assert data["modules"][0]["requirements"][0]["points"][0]["cases"][0] == {"id": "TC-001", "title": "重选", "priority": "", "exec_ids": ["AMS-001"], "open_points": 0}
    kinds = {(g["req_id"], g["kind"]) for g in data["gaps"]}
    assert ("AR-1", "no_case") in kinds and ("AR-2", "loose_case") in kinds, "出了用例以后，没有用例的测试点和没挂上测试点的用例也要列出来"

    page = render_design_map_html(record)
    assert "选网测试设计 - 测试架构图" in page and "__MAP_" not in page
    assert "没有可用邻区<\\/script>" in page, "数据里的 </script> 不能截断页面脚本"
    assert "http://" not in page and "https://" not in page, "页面要能离线打开，不引用外部资源"


def test_design_map_endpoint_serves_the_archived_design(tmp_path, monkeypatch):
    import main
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "HISTORY_DIR", tmp_path)
    record = main._write_design_history_record(dict(_design_record(), record_id="abcdef123456"))
    assert main._history_summary(record)["map_url"] == "/api/design-history/abcdef123456/map"
    resp = TestClient(main.app).get("/api/design-history/abcdef123456/map")
    assert resp.status_code == 200 and "text/html" in resp.headers["content-type"] and "SR 10 选网" in resp.text


def test_selected_test_types_drive_design_advice_and_map():
    from core.design_map import build_design_map
    from core.scope import review_note, scope_note, selected_test_types, type_gaps

    assert selected_test_types({}) == ["functional"], "没选时只做功能"
    shared = {"product_profile": {"test_types": ["性能", "stability", "functional"]}}
    types = selected_test_types(shared)
    assert types == ["functional", "performance", "stability"]
    assert "样本量" in scope_note(types) and "acceptance.kpi" in review_note(types) and "性能" not in review_note(["functional"]).split("。", 1)[1]

    record = _design_record()
    reqs, rows = record["requirement_spec"]["final_requirements"], record["test_design_spec"]["integrated_matrix"]
    rows.append({"row_id": "ROW-1-3", "req_id": "AR-1", "technique": "performance", "scenario": "重选时延统计"})
    gaps = {(g["module"], g["test_type"]) for g in type_gaps(rows, reqs, types)}
    assert gaps == {("SR 10 选网", "stability"), ("SR 20 位置", "performance"), ("SR 20 位置", "stability")}
    assert type_gaps(rows, reqs, ["functional"]) == []

    record["test_design_spec"]["test_types"] = types
    data = build_design_map(record)
    assert data["stats"]["by_type"] == {"functional": 3, "performance": 1}
    assert sum(1 for g in data["gaps"] if g["kind"] == "type_missing") == 3
    assert [t["selected"] for t in data["test_types"]] == [True, True, True]
    record["test_design_spec"]["test_types"] = ["functional"]
    assert not [g for g in build_design_map(record)["gaps"] if g["kind"] == "type_missing"], "没选的类型不算缺口"
