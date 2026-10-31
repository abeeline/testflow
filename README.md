# TestFlow

基于 PocketFlow 的 **LLM 系统测试 Agent Web 平台**，面向通信/模组测试场景，覆盖从需求分析到测试脚本与联机调试的全流程。

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

## 目录说明

- Web 应用目录：`cookbook/pocketflow-system-test-agent-web`
- 一键部署脚本：`deploy/vps_deploy.sh`
- 一键更新脚本：`deploy/update.sh`

---

## 本地启动

```bash
cd cookbook/pocketflow-system-test-agent-web
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8010
```

访问：`http://127.0.0.1:8010`

生成测试设计后，可在左侧 `测试设计历史` 中查看归档记录与固定 URL 设计文档。

---

## VPS 一键安装（首次）

> 适用 Ubuntu 24.04 LTS

```bash
cd /opt
git clone https://github.com/abeeline/testflow.git
cd /opt/testflow
bash deploy/vps_deploy.sh
```

默认服务名：`testflow-web`

---

## VPS 一键更新（增量，不重装）

```bash
cd /opt/testflow
bash deploy/update.sh
```

`update.sh` 会自动执行：

1. `git pull origin main`
2. 校验/创建虚拟环境
3. 安装依赖
4. 重启 `testflow-web`
5. 健康检查 `http://127.0.0.1:8010/`

### 可选环境变量

```bash
SERVICE_NAME=testflow-web APP_PORT=8010 bash deploy/update.sh
```

---

## 环境变量配置

编辑：

```bash
/opt/testflow/cookbook/pocketflow-system-test-agent-web/.env
```

修改后重启服务：

```bash
sudo systemctl restart testflow-web
```

---

## 运维常用命令

```bash
# 查看服务状态
sudo systemctl status testflow-web --no-pager -l

# 查看实时日志
sudo journalctl -u testflow-web -f

# 重启服务
sudo systemctl restart testflow-web
```

## 关键接口

```bash
# 历史测试设计列表
GET /api/design-history

# 历史测试设计详情
GET /api/design-history/{record_id}

# 固定 URL 测试设计文档
GET /api/design-history/{record_id}/document
```

---

## 常见问题

### 1) `detected dubious ownership`

```bash
git config --global --add safe.directory /opt/testflow
```

### 2) `uvicorn: command not found`

使用虚拟环境启动：

```bash
cd /opt/testflow/cookbook/pocketflow-system-test-agent-web
source .venv/bin/activate
python -m uvicorn main:app --host 127.0.0.1 --port 8010
```

### 3) 更新后页面还是旧版本

- 强制刷新浏览器（Cmd/Ctrl + Shift + R）
- 确认服务已重启
- 确认 `git pull` 已拿到最新提交
