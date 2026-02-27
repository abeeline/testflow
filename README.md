# TestFlow

基于 PocketFlow 的 **LLM 系统测试 Agent Web 平台**，面向通信/模组测试场景，覆盖从需求分析到测试脚本与联机调试的全流程。

## 项目定位

TestFlow 不是通用 Demo，而是一个可落地的测试生产系统，核心目标：

- 输入需求（单条完整需求描述）
- 自动生成测试需求稿（含三人评审）
- 生成测试设计稿（目标 + 覆盖矩阵 + 整合矩阵）
- 生成测试用例稿与脚本参考
- 支持 ADB / AT 串口联机调试与在线执行
- 支持 ATSpec / Profile / EFSM/MBT 的配置编译与可视化

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

### 3) 测试脚本与联机调试

- Agentic Coding 对话生成/修改脚本
- Web ADB / Web Serial AT 两种自动化方式
- 在线调试与在线执行
- 设备发现接口：ADB 设备列表、串口列表

### 4) AT 测试 Agent

- 基准：3GPP 27.007 + 27.005（ATSpec）
- 支持 Manifest（删减/策略）与 Extension（厂商自定义AT）
- EFSM/MBT 编译输出 active 模型并可视化

### 5) 数据导出

- Excel 一次导出全流程：
  - 需求输入
  - 测试需求稿
  - 三人评审
  - 测试设计目标/矩阵
  - 测试用例/步骤
  - RawJSON

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

