"""程序目录与数据目录。

数据目录保存用户配置、设计历史、RAG 文档和修改过的 Prompt。默认就是程序目录；
Windows 发布包里 start.bat 会把它指到包内的 data\\ 目录，升级时整体拷走 data 即可。
"""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("TESTFLOW_DATA_DIR") or APP_DIR).resolve()

STATIC_DIR = APP_DIR / "static"
DEFAULT_PROMPT_DIR = APP_DIR / "prompts"
PROMPT_OVERRIDE_DIR = DATA_DIR / "config" / "prompts"
CONFIG_DIR = DATA_DIR / "config"
HISTORY_DIR = DATA_DIR / "history" / "designs"
RAG_DIR = DATA_DIR / "rag_data"


def prompt_path(name: str) -> Path:
    """网页上改过的模板保存在数据目录，优先使用；否则用程序自带的默认模板。"""
    override = PROMPT_OVERRIDE_DIR / name
    return override if override.exists() else DEFAULT_PROMPT_DIR / name
