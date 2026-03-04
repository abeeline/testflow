# ATest (Standalone)

AT测试Agent独立应用，可单独部署运行。
与 `testflow-web` 进程级隔离，支持独立 LLM 配置和独立数据目录。

## 启动

```bash
cd /path/to/PocketFlow-main
python3 -m uvicorn atest.app:app --host 0.0.0.0 --port 8011
```

访问：`http://<host>:8011`

## 说明

- 独立前端：`atest/static`
- 独立后端入口：`atest/app.py`
- 首次启动会把基线文件复制到 `atest/data`，后续读写均在 `atest/data`（不污染 testflow 运行态）
- 复用主项目编译逻辑，但路径已重绑定到 `atest/data`，可单独运维
- 独立部署时请确保主项目依赖已安装（含 FastAPI、Pydantic、LLM 相关依赖）

## 独立 LLM 配置

1. 复制配置模板：

```bash
cp atest/.env.example atest/.env
```

2. 编辑 `atest/.env`：

- `ATEST_LLM_API_BASE`
- `ATEST_LLM_API_KEY`
- `ATEST_LLM_MODEL`

可选独立数据目录：

- `ATEST_DATA_DIR=/your/path/atest-data`

## 健康检查

```bash
curl http://127.0.0.1:8011/healthz
```
