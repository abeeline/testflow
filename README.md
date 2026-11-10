# TestFlow

基于 PocketFlow 的 **LLM 系统测试 Agent Web 平台**，面向通信/模组测试场景，覆盖从需求分析、测试设计到可执行用例的全流程。

## 项目定位

TestFlow 不是通用 Demo，而是一个可落地的测试生产系统，流程按 3GPP 蜂窝通信软件的测试设计过程组织：

- 输入需求（需求描述、需求文档/RAG 资料、Bugzilla 研发需求/Bug）
- 测试需求分析：需求解析 → 三方评审（规范 / 运营商 / 体验）→ 综合定稿，问题大多由 AI / 知识库自行确认
- 测试设计：测试目标 → 按测试技术（正常 / 异常 / 边界 / 定时器 / 冲突 / 移动性 / 互操作 / 能力组合 / 性能 / 长稳）导出测试点，每个测试点写 3GPP 测试目的（with / when / then）
- 测试用例：按 TS 38.523-1 / 36.523-1 的写法生成 3GPP 风格测试用例描述（TCD）：初始条件、关键配置、特定消息内容、带方向和判定点的测试步骤
- 可执行用例：由 TCD 直接投影成 Artemis / AT Agent / Amarisoft / 协议仪表四类 JSON 草稿，LLM 做平台适配，并输出追溯矩阵（Bug → 需求 → 测试点 → 用例 → 可执行 case）
- 可分步评审，也可“一键生成全部”

架构说明与本次重构的 review 结论见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

> AT 指令测试建模（ATSpec/EFSM/MBT）与 ADB/串口联机执行已移除，相关能力由独立的 AT agent 项目承担。

---

## 重要功能

### 1) 需求与评审（HITL）

- 三人格并行评审：Spec / Carrier / UX
- `issues` 与 `open_questions` 区分处理
- 支持多轮需求迭代（v1→v2→v3）
- SSE 推送到 Bot：任务状态、异常、待确认事项

### 2) 测试设计与用例（3GPP 对齐）

- 需求到设计的可追踪映射（REQ → Objective → 测试点 ROW → TC → 可执行 case）
- 测试设计一次生成目标 + 整合矩阵；有需求没被覆盖时只为缺口补测试点（`integrated_matrix_designer.txt`），不再整份重做
- 每个测试点带 `technique`（测试技术）、`test_purpose`（with / when / then）、`references`（规范条款）；P0/P1 需求只有正常流程时给出设计提示
- 测试用例是 3GPP 风格测试用例描述（TCD，`core/tcd.py`，提示词 `test_case_tcd.txt`）：
  `test_purpose`、`applicability`、`references`、`initial_conditions`（网络侧 / UE / preamble）、`configuration`（cells / core / ue）、
  `message_contents`（相对默认消息内容的 IE 修改）、`procedure`（St、发起方、UL/DL、层、消息、msg_ref、期望、判定点）、`parameter_variations`、`postamble`、`pass_fail`
  旧字段 `preconditions` / `steps` / `expected` 仍然保留，旧历史记录照常可用
- 质量门（`core/quality.py`）先做确定性修复：需求写明的配置、数值门限没进矩阵或用例时直接按原值补入（用例里标为 `patched`）；
  结构不合格的用例（缺 when/then、没有判定步骤、模拟基站/仪表用例没有小区配置或信令步骤……）只返工对应测试点，不重跑全部
- 需求配置按“参数名 + 取值”核对（`utils/req_configs.py: config_status`），不会把步骤号或别的参数里的数字误当成已落地；
  用例里同名参数取值不同时标为 `conflict`：先让模型改一次，仍不一致就保留原值、把需求值另存为“参数名（需求值）”并写进待确认项；
  需求对同一参数给了多个取值时按扫描处理，补进 `parameter_variations`
- 专家评审（提示词 `test_case_reviewer.txt`，测试设计页可关）：用例写完后另起一次调用，让模型以评审者身份检查协议正确性
  （消息名、方向、顺序、定时器和原因值语义）、测试目的能否判定、是否与需求和测试点一致、实网用例是否依赖了网络侧控制；
  严重问题并入返工反馈，一般意见留在用例的 `review_notes` 里（页面和 Excel 可见）
- 用例分批并行生成，编号按矩阵行顺序统一（不同批次不再撞号）；输出被截断时自动把这一批对半拆开重试
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
| 模拟基站 | Amarisoft 环境 | `testflow-amarisoft-case` v2：关键 PHY/小区/核心网参数、需定制的消息 IE、步骤、期望信令、通过标准、需求配置落地情况 | Amarisoft Agent 生成配置并执行 |
| 协议流程 | 协议分析仪环境 | `testflow-protocol-test-requirement` v3：消息模板 + IE 覆盖值、信令流程、参数组合、检查点、规范条款、需求配置落地情况 | PRTest 后续编写 XML + Python |

**需求写明的配置不丢**（`utils/req_configs.py`）：

- 需求解析时把原文写明的配置（频段、频点、带宽、SCS、定时器、DRX/PSM、测量门限、IE 取值、拒绝原因、APN 等）原样记到 `explicit_configs`（name / value / source_text），综合评审丢掉时按 req_id 自动补回；测试设计和用例生成要求这些值原样进 `key_configuration` 和步骤参数
- 生成 Amarisoft / 协议仪表 case 时，把关联需求的 `explicit_configs` 和需求原文中的配置行一起交给 LLM，要求一字不改地落到 `cell_config` / `core_config` / `message_configs` 等字段
- 生成后逐项核对：每个 case 的 `requirement_configs` 标明每项需求配置 `applied`（已落地）/ `patched`（模型漏了，已按需求原值补入，`applied_to` 写明补到哪）/ `not_applicable` / `conflict`；bundle 的 `source_requirement.config_lines` 保留需求原文配置行并标出取值是否出现在 case 中（`other_route` 表示落在了其他平台的用例里，只有所有平台都没有才告警）
- 实网用例（Artemis / AT Agent）的 `expected_result` 会保留用例通过标准里的数值门限，模型改写时丢了就按原文补回；TCD 里写明的消息 IE 被模型漏掉时也按草稿补回
- bundle 顶部 `field_guide` 说明每个字段的含义，下游 Agent 无需额外文档；Excel 导出新增“需求配置落地”页

**由 TCD 投影，LLM 只做平台适配**：每条用例先由 `core/tcd.py: project()` 确定性映射出该平台的草稿（配置、消息内容、信令流程、判定点一个不少），
草稿作为 `{draft_json}` 交给路线 LLM 补平台细节；LLM 输出缺的字段、小区/核心网配置里漏掉的键会用草稿补回。LLM 不可用或失败时直接导出草稿，内容同样完整。
Amarisoft case 升到 v3、协议测试需求升到 v4（新增 `test_purpose`、`technique`、`references`、`procedure[].verdict`、协议路线的 `core_config`，都是新增字段，旧字段不变）。

各路线提示词在 `prompts/exec_case_*.txt`，可在 Prompt Settings 中调整。自定义过旧模板的，如果模板里没有 `{draft_json}` 会给出告警，建议恢复默认模板。

### 5) 数据导出

- Excel 一次导出全流程：
  - 需求输入
  - 测试需求稿
  - 三人评审
  - 测试设计目标/矩阵（含测试技术、测试目的）
  - 测试用例（测试目的、参考条款、初始条件、关键配置、步骤）
  - 测试步骤（每步一行：发起方、方向、层、消息、期望、判定点）
  - 消息内容（每个 IE 一行：消息、IE 路径、取值、扫描参数）
  - 追溯矩阵（生成可执行用例后）
  - RawJSON

### 6) 项目 / Product

- 每个测试设计都归属一个项目（Product），左侧边栏顶部切换“当前项目”，新生成的测试设计归档到当前项目
- “项目 / Product”页：新建、编辑、删除项目；可把“需求准备”页的产品特性和测试环境勾选保存为项目默认值，切换项目时自动勾选
- 项目资料：每个项目有自己的资料库，生成测试需求时自动检索“当前项目资料 + 公共资料”，命中片段标明来源
- 测试设计历史默认只显示当前项目，可勾选“显示全部项目”，也可以把记录移到其他项目
- 升级前的历史记录自动归到“默认项目”；默认项目不能删除，有测试设计的项目需先移走记录再删除
- 知识库（MCP）：“系统设置 → 知识库”只需填公共知识库的 MCP 地址（如 `http://aifoundry.example.com:8099/mcp/server/<id>/mcp`）；每个项目可在项目页另填自己知识库的 MCP 地址。调用方式为 JSON-RPC：先 `tools/list` 取工具名，再 `tools/call` 传入带“引用来源”提示词的问题，回答文本和引用资料一起带进上下文（`utils/mcp_kb.py`）。生成测试需求时同时检索项目知识库、公共知识库和本地资料，某个知识库连不上不影响其他来源（接口：`GET/POST /api/settings/kb`、`POST /api/settings/kb/test`）
- 资料检索规则（`utils/knowledge.py`）：
  - 可信度：用户粘贴 > 项目知识库 > 项目本地资料 > 公共知识库 > 公共本地资料，冲突时以项目资料为准；每个来源有条数上限，总字数不超过 6000，片段编号 `[K-n]`
  - 查询词：项目来源用需求原文；公共知识库用从需求里提取的协议关键词（流程、消息、定时器、条款号、频段）
  - 测试需求评审：三人评审后，最多 8 个问题先查知识库（产品行为类查项目知识库，协议类查公共知识库），有明确依据的由 AI 改答案并标出处，资料矛盾的留给用户确认
  - 测试设计：每条需求单独查项目和公共知识库，用于参数取值、定时器、信令流程和条款引用
  - 用到的资料写进设计历史和测试设计文档的“参考资料”
  - 配置了公共知识库后，需求准备页不再提供“存入公共资料”
- 接口：`GET/POST /api/projects`、`GET/PUT/DELETE /api/projects/{id}`、`GET/POST /api/projects/{id}/docs`、`DELETE /api/projects/{id}/docs/{doc_id}`、`POST /api/design-history/{id}/project`

### 7) 测试设计历史目录

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

配置、项目、设计历史、RAG 文档和网页上改过的 Prompt 都在发布包的 `data\` 目录；升级时把旧版本的 `data\` 复制到新版本即可。

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
flow.py / nodes.py PocketFlow 流水线与各节点（只做编排）
core/              领域层：llm.py（LLM 运行时）、tcd.py（3GPP 测试用例描述与投影）、quality.py（质量门）、environments.py（测试环境能力）、events.py（任务事件流）
exec_cases.py      可执行用例（按验收方案分流）
tests/             离线测试（假 LLM）
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

LLM 运行时（`core/llm.py`）：

- 提示词模板的 `[System]` / `[User]` 两段分别作为 system / user 消息发送
- 输出不是合法 JSON 或不符合 schema 时，把上次输出和具体错误回灌给模型修正（自修复），不再原样重发
- `finish_reason=length`（输出被截断）时，批量任务自动对半拆批重试；单条任务要求模型精简后重写
- 顶层是对象的输出自动请求 JSON 模式（`response_format=json_object`），接口不支持时自动退回
- 参数兼容：接口不接受自定义 `temperature`，或要求用 `max_completion_tokens` 代替 `max_tokens`（部分推理模型）时，自动去掉 / 换用后重发，并记住这个接口的习惯
- “单次输出上限”可在大模型设置里填（默认 0 = 用接口默认值）；用例经常被截断时调大
- 同时在途的请求数全局限制为 4（环境变量 `TESTFLOW_LLM_CONCURRENCY` 可调）；限流 / 5xx / 网络错误退避重试，key 错、模型名错这类错误立即报出
- LLM 请求都在线程池里执行，生成过程中页面其他操作（助手、设置、历史）不受影响
- 每个阶段统计 LLM 调用、自修复、失败次数和 token 用量，显示在运行状态里（结果字段 `llm_usage`）

## 一键生成与助手

- 需求准备页“⚡ 一键生成全部”：需求评审 → 测试设计 → 测试用例 → 可执行用例一次跑完（`POST /api/stage/auto/start`），评审问题全部采用 AI / 知识库答案，各页面边跑边刷新；之后仍可回到任一页面改答案、分步重跑
- 进度通过 SSE 推送（`/api/stage/{job_id}/stream`），事件带序号；连接中断后浏览器自动重连并从断点续收，长任务不会因为网络抖动而“失败”
- 没配大模型时一键生成也能跑通：按规则给出每条需求一个正常流程测试点的骨架，方便先联调流程和导出格式
- 右下角助手能看到当前会话的需求、测试点、用例和告警摘要，可以直接问“TC-003 为什么用协议仪表”“REQ-002 还缺哪些异常场景”

## 测试

```bash
pip install -r requirements.txt pytest httpx
python -m pytest -q        # 用假 LLM 离线跑完整流水线
```

相关接口：`GET/POST /api/settings/llm`、`POST /api/settings/llm/test`。

## 关键接口

```
GET  /api/projects                           项目 / Product 列表
GET  /api/design-history?project_id=         历史测试设计列表（可按项目筛选）
GET  /api/design-history/{record_id}         历史测试设计详情
GET  /api/design-history/{record_id}/document 固定 URL 测试设计文档
POST /api/stage/{stage}/start                启动阶段任务（design / testcases / exec_cases / auto）
POST /api/export/testcases.xlsx              导出 Excel
```
