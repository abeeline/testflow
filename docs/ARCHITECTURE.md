# TestFlow 架构（v0.6）

## 1. Review 结论（重构前的主要问题）

| # | 问题 | 影响 |
| --- | --- | --- |
| 1 | 测试用例只用 9 个通用动作（`SET_DEVICE_STATE`、`TRIGGER_REGISTRATION`…）描述步骤，没有消息、方向、IE、判定点 | 协议信息在“测试用例”这一环丢失，可执行用例阶段只能让 LLM 从需求重新推一遍，两次推导容易不一致 |
| 2 | 测试设计先让 LLM 输出整合矩阵，随后整份丢弃，再调一次 LLM 重新生成 | 多一次大调用，两次结果互相不一致 |
| 3 | 重试时只有可执行用例模板带 `{last_error}`，其他模板重试是原样重发 | 校验失败基本白重试；也没有截断识别，长输出（协议 IE）被截断后只能降级 |
| 4 | 模板的 `[System]` / `[User]` 整段当作 user 消息发送 | 角色指令没有放进 system，约束力弱 |
| 5 | 用例分批并行生成，每批都从 `TC-001` 编号 | 不同批次撞号，可执行用例按 `tc_id` 分流时会串号 |
| 6 | 质量门不通过就整份重跑；需求配置、数值门限丢失也靠 LLM 重跑 | 成本高且不保证修好 |
| 7 | 测试设计没有测试技术和测试目的（TP）的概念 | 偏向“正常流程 + 维度组合”，异常、边界、定时器、冲突场景容易漏 |
| 8 | 每次可执行用例调用都塞进全部需求；LLM 失败时 Amarisoft / 协议用例几乎是空的 | 提示词浪费；降级结果不能用 |
| 9 | 只能一步步点；助手不知道当前会话内容 | 易用性差，LLM 能力没用上 |

## 2. 新流水线

```
需求原文 / Bugzilla / RAG / MCP 知识库
   │
   ▼  测试需求分析（HITL 多轮，或一键模式单轮）
需求解析 ─► 三方评审（规范 / 运营商 / 体验）─► 综合定稿   explicit_configs 原样保留，丢了按 req_id 补回
   │
   ▼  测试设计（test_designer.txt，一次生成）
测试目标 + 整合矩阵（测试点）
   每行：technique · test_purpose(with/when/then) · key_configuration · pass_criteria · references · test_environment
   │  设计质量门（确定性）：补入需求配置 / 数值门限；缺覆盖 → 只为缺口调用 integrated_matrix_designer.txt，再不行按规则补行
   ▼  测试用例（test_case_tcd.txt，每批 4 行并行，截断自动对半拆）
3GPP 测试用例描述 TCD（core/tcd.py）
   test_purpose · applicability · references · initial_conditions · configuration(cells/core/ue)
   · message_contents(IE 修改) · procedure(St/发起方/UL-DL/层/消息/msg_ref/期望/判定) · parameter_variations · pass_fail
   │  用例质量门（core/quality.py）：补入需求配置（标 patched）；结构不合格 → 只返工对应测试点
   ▼  可执行用例（exec_cases.py）
TCD ──project()──► 平台草稿 ──LLM 平台适配──► 合并（缺的字段 / 漏的配置键用草稿补）──► 需求配置落地核对
   Artemis（flash）· AT Agent（at）· Amarisoft v3 · 协议测试需求 v4 · 追溯矩阵
```

## 3. 分层

| 层 | 文件 | 职责 |
| --- | --- | --- |
| 接口 / 任务 | `main.py` | FastAPI、HITL 任务、阶段任务（含 `auto` 一键模式）、历史、Excel、助手 |
| 编排 | `flow.py`、`nodes.py`、`exec_cases.py` | PocketFlow 节点，只负责取数、调用 core、写回 shared、发进度事件 |
| 领域 | `core/llm.py` | LLM 运行时：system/user 拆分、自修复、截断识别与拆批、JSON 模式、用量统计 |
|  | `core/tcd.py` | TCD 结构、规范化（兼容旧格式）、需求配置补入、向四类平台的投影 |
|  | `core/quality.py` | 设计 / 用例质量门：确定性修复 + 定向返工 |
|  | `core/environments.py` | 测试环境目录、能力边界（能做 / 不能做）、规则兜底推荐 |
| 基础 | `utils/` | LLM 客户端、提示词加载、知识库（MCP）、RAG、项目、Bugzilla、需求配置抽取 |

## 4. LLM 用法要点

- **结构化中间表示**：TCD 是 LLM 与下游平台之间的“合同”。LLM 在信息最全的时候（有需求、测试点、知识库片段）一次写出协议细节，后面只做投影和适配，不再重新推导。
- **自修复而不是重试**：校验错误原文回灌，模型在原答案上改；截断时拆批而不是重发同样长的请求。
- **确定性兜底**：需求写明的取值、数值门限由代码保证进入矩阵、用例和可执行用例；LLM 漏了也能补上，并在结果里标明（`patched` / `missing`）。
- **定向返工**：质量门只把不合格的测试点送回 LLM，并附上逐条问题。
- **上下文感知助手**：前端把当前会话摘要（需求、配置、测试点、用例、告警）随问题发给助手。

## 5. 兼容性

- 旧历史记录里的用例（`steps` 格式）在生成可执行用例时会先转成 TCD，页面按旧格式展示。
- 规范化后的用例仍保留 `preconditions` / `steps` / `expected` / `pass_fail` 字段。
- 可执行用例格式只新增字段：Amarisoft v2→v3、协议 v3→v4；Artemis / AT Agent 格式不变。
- 提示词：`test_case_generator.txt` 由 `test_case_tcd.txt` 取代；`integrated_matrix_designer.txt` 改为只补缺口；四个 `exec_case_*.txt` 新增 `{draft_json}`。网页上改过这些模板的，建议恢复默认后再按需调整。
