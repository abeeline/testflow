# PocketFlow System Test Agent (Web)

基于 PocketFlow 的 LLM 多智能体系统测试流水线（Web 形态），覆盖：

1. 需求分析（Req Parse + 三人格并行审计 + 仲裁融合）
2. 测试设计（Objective + CoverageMatrix）
3. 用例生成（TestCaseSpec）
4. 执行准备（ScriptSpec + 测试代码参考）

## 流水线

- Requirement Intake
- Req Parse & Normalize
- Tri-Persona Review (Spec Lawyer / Carrier Reviewer / UX Advocate)
- Synthesis & Decision
- Test Design
- Test Case Generation
- Script Planning (Harness Mapper)
- Script Generation (Script Writer)

## Prompt 模板固化

每个 agent 独立模板文件位于：

`/Users/geminipro/Documents/PocketFlow-main/cookbook/pocketflow-system-test-agent-web/prompts`

- `req_parse.txt`
- `review_spec_lawyer.txt`
- `review_carrier.txt`
- `review_ux_advocate.txt`
- `synthesis_arbiter.txt`
- `test_designer.txt`
- `test_case_generator.txt`
- `harness_mapper.txt`
- `script_writer.txt`

## 严格 JSON Schema 校验 + 自动重试

JSON 类型 agent 统一通过 `run_json_agent_with_retry` 执行：

- 解析 LLM 输出为 JSON
- 严格做 schema 校验（优先 `jsonschema`，缺失时走内置严格后备校验）
- 校验失败自动重试（默认 2 次）
- 超过重试次数后回退 fallback，并在 `warnings` 标注原因

实现位置：

- `/Users/geminipro/Documents/PocketFlow-main/cookbook/pocketflow-system-test-agent-web/utils/agent_runner.py`
- `/Users/geminipro/Documents/PocketFlow-main/cookbook/pocketflow-system-test-agent-web/utils/schema_validation.py`

## 启动

```bash
cd /Users/geminipro/Documents/PocketFlow-main/cookbook/pocketflow-system-test-agent-web
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

打开 [http://127.0.0.1:8010](http://127.0.0.1:8010)

## LLM 配置（可选）

未配置 LLM 时系统会使用降级模板继续跑完整流程。
程序会自动加载项目目录下的 `.env`（`/Users/geminipro/Documents/PocketFlow-main/cookbook/pocketflow-system-test-agent-web/.env`）。

```bash
export LLM_API_BASE="https://api.openai.com/v1"
export LLM_API_KEY="<your-key>"
export LLM_MODEL="gpt-4.1-mini"
```

## API

`POST /api/generate`

```json
{
  "requirements": ["需求1", "需求2"],
  "rag_context": "可选",
  "framework_capability_catalog": "可选",
  "capabilities": {
    "harnesses": ["ANDROID_UIA", "PY_AT", "QXDM"],
    "actions_supported": {"SET_DEVICE_STATE": ["adb"]}
  },
  "action_vocabulary": ["SET_DEVICE_STATE", "TRIGGER_REGISTRATION", "WAIT", "CHECK", "COLLECT_LOG"],
  "assertion_vocabulary": ["ASSERT_IMS_REGISTERED"]
}
```

响应包含：

- `artifacts_structured`: requirement_spec / test_design_spec / test_case_spec / script_spec
- `artifacts`: 四类可读文本（测试需求、测试设计稿、测试用例、测试代码参考）
- `missing_inputs`: RAG 与能力清单缺失提示
