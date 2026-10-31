# TestFlow

基于 PocketFlow 的 **LLM 系统测试 Agent Web 平台**，面向通信/模组测试场景，覆盖从需求分析、测试设计到可执行用例的全流程。

## 项目定位

TestFlow 不是通用 Demo，而是一个可落地的测试生产系统，核心目标：

- 输入需求（需求描述、需求文档/RAG 资料、Bugzilla 研发需求/Bug）
- 自动生成测试需求稿（含三人评审）
- 生成测试设计稿（目标 + 覆盖矩阵 + 整合矩阵）
- 生成测试用例稿
- 按验收方案生成可直接执行的 JSON case，并输出追溯矩阵（Bug → 需求 → 用例 → 可执行 case）

> AT 指令测试建模（ATSpec/EFSM/MBT）与 ADB/串口联机执行已移除，相关能力由独立的 AT agent 项目承担。

---

## 重要功能

### 1) 需求与评审（HITL）

- 三人格并行评审：Spec / Carrier / UX
- `issues` 与 `open_questions` 区分处理
- 支持多轮需求迭代（v1→v2→v3）
- SSE 推送到 Bot：任务状态、异常、待确认事项

### 2) 测试设计与用例

- 需求到设计的可追踪映射（REQ → Objective → Matrix → TC）
- 设计质量审查节点（Supervisor）自动回流
- 用例生成支持批量并发与稳定产出
- 测试设计完成后自动归档到“测试设计历史”
- 自动生成标准测试设计文档（HTML），支持固定 URL 查看与分享
- 可从历史记录重新载入当前会话，或继续生成测试用例

### 3) Bugzilla 需求接入

- 需求准备页填写 Bugzilla 地址和 API Key（兼容 Bugzilla 5.x，带 key 时走 JSON-RPC，不把 key 放进 URL）
- 按 Bug 编号读取标题、状态、描述和评论，可排除机器人等评论作者，内容追加到需求描述，Bug 编号进入追溯矩阵
- 接口：`GET/POST /api/bugzilla/settings`、`POST /api/bugzilla/fetch`

### 4) 可执行用例（按验收方案分流）

每条测试用例按测试环境自动分流（`/api/stage/exec_cases/start`）：

| 验收方案 | 判定 | 导出格式 | 去向 |
| --- | --- | --- | --- |
| 实网手机 | 实网环境 + 手机类产品 | `artemis-case-library` v1，`profile=flash` | Artemis 用例库导入 |
| 实网模组 / AT 指令 | 实网环境 + 模组类产品，或用例含 AT 指令 | `artemis-case-library` v1，`profile=at` | AT Agent 用例库导入 |
| 模拟基站 | Amarisoft 环境 | `testflow-amarisoft-case` v1：关键 PHY/小区/核心网参数、步骤、期望信令、通过标准 | Amarisoft Agent 生成配置并执行 |
| 协议流程 | 协议分析仪环境 | `testflow-protocol-test-requirement` v1：信令流程、关键 IE、参数组合、检查点、规范条款 | PRTest 后续编写 XML + Python |

各路线提示词在 `prompts/exec_case_*.txt`，可在 Prompt Settings 中调整。LLM 不可用时会按用例内容生成降级 case，保证每条用例都有落地结果。

### 5) 数据导出

- Excel 一次导出全流程：
  - 需求输入
  - 测试需求稿
  - 三人评审
  - 测试设计目标/矩阵
  - 测试用例/步骤
  - 追溯矩阵（生成可执行用例后）
  - RawJSON

### 6) 测试设计历史目录

- 左侧菜单提供“测试设计历史”
- 每次完成“测试设计稿”都会自动生成一条历史记录
- 历史记录包含：
  - 原始需求输入
  - 产品通信背景与支持特性
  - 测试需求稿
  - 三人评审
  - 测试设计稿
  - 已生成的测试用例（如果后续执行过）
- 支持固定 URL 文档：
  - `/api/design-history/{record_id}/document`
- 支持从历史记录继续生成测试用例，无需重新跑前置设计

---

## 运行方式

### Windows 发布包（推荐）

1. 下载 `TestFlow-<版本>-win64.zip`，完整解压到任意目录
2. 双击 `start.bat`，浏览器会自动打开 `http://127.0.0.1:8010/`（端口被占用会自动顺延）
3. 首次使用在左下角“系统设置 → 大模型”里填写 OpenAI 兼容接口地址、API Key、模型名称，点“测试连接”后保存

发布包内置 Python，不需要另外安装。可选参数：`start.bat --port 9000`、`start.bat --host 0.0.0.0`（局域网访问）、`start.bat --no-browser`。

配置、设计历史、RAG 文档和网页上改过的 Prompt 都在发布包的 `data\` 目录；升级时把旧版本的 `data\` 复制到新版本即可。

### 从源码运行

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                 # 等价于 start.bat；数据默认写在源码目录
```

Windows 上也可以直接双击源码根目录的 `start.bat`：没有内置 Python 时，它会用系统 Python 创建 `.venv` 并安装依赖。

### 打 Windows 发布包

```bash
python scripts/build_windows_release.py --version 0.1.0
# 产物：release/TestFlow-0.1.0-win64.zip
```

脚本可以在 macOS / Linux / Windows 上运行，会从 nuget.org 下载官方 Windows Python（3.12）并从 PyPI 预装 win_amd64 依赖。

---

## 目录结构

```
main.py            FastAPI 接口
flow.py / nodes.py PocketFlow 流水线与各节点
exec_cases.py      可执行用例（按验收方案分流）
schemas.py         JSON Schema
prompts/           各 agent 的默认 Prompt 模板
static/            Web 前端
utils/             LLM 客户端与配置、Bugzilla、RAG、路径
pocketflow/        PocketFlow 核心（约 100 行）
run.py             启动入口
start.bat          Windows 启动脚本
scripts/           打包脚本
packaging/windows/ 发布包附带的使用说明
```

## 大模型配置

只支持 OpenAI 兼容接口（`POST {base}/chat/completions`），在网页“系统设置 → 大模型”里配置，保存在数据目录的 `config/llm-settings.json`。接口只返回“是否已配置 key”，不回显 key 本身；修改接口地址时不会沿用旧 key。

相关接口：`GET/POST /api/settings/llm`、`POST /api/settings/llm/test`。

## 关键接口

```
GET  /api/design-history                     历史测试设计列表
GET  /api/design-history/{record_id}         历史测试设计详情
GET  /api/design-history/{record_id}/document 固定 URL 测试设计文档
POST /api/stage/{stage}/start                启动阶段任务（design / testcases / exec_cases）
POST /api/export/testcases.xlsx              导出 Excel
```
