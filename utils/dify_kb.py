"""Dify 知识库检索。

“系统设置 → 知识库”里填 Dify 接口地址和公共知识库的 App Key，保存在 config/kb-settings.json。
每个项目可以另配一个自己知识库的 App Key（存在项目里）。检索时同时查“项目知识库 + 公共知识库”，
把 Dify 返回的引用片段（metadata.retriever_resources）带进测试需求分析的上下文。

调用的是 Dify 文本生成应用的 POST {base}/completion-messages，输入变量名为 query。
"""
import json
import os
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from utils.paths import CONFIG_DIR

SETTINGS_PATH = CONFIG_DIR / "kb-settings.json"
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_QUERY_CHARS = 500
_lock = threading.Lock()


def normalize_base_url(value: str) -> str:
    raw = (value or "").strip().rstrip("/")
    if not raw:
        return ""
    p = urlsplit(raw)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("请输入完整的 http(s) 地址，例如 http://dify.example.com/v1")
    if raw.endswith("/completion-messages"):
        raw = raw[: -len("/completion-messages")]
    return raw


def _clamp(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return default


class KBSettings:
    """读写知识库连接配置。接口只回显 key 是否已配置，不回显 key 本身。"""

    def __init__(self, path: Path = SETTINGS_PATH):
        self.path = Path(path)

    def read(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8")) or {}
            except Exception:
                data = {}
        return {
            "base_url": str(data.get("base_url") or ""),
            "api_key": str(data.get("api_key") or ""),
            "timeout": _clamp(data.get("timeout"), DEFAULT_TIMEOUT, 5, 300),
            "max_query_chars": _clamp(data.get("max_query_chars"), DEFAULT_MAX_QUERY_CHARS, 20, 8000),
        }

    def public(self) -> Dict[str, Any]:
        cfg = self.read()
        return {
            "base_url": cfg["base_url"],
            "timeout": cfg["timeout"],
            "max_query_chars": cfg["max_query_chars"],
            "key_configured": bool(cfg["api_key"]),
            "enabled": bool(cfg["base_url"]),
        }

    def merged(self, base_url: str, api_key: str = "", clear_key: bool = False,
               timeout: Optional[int] = None, max_query_chars: Optional[int] = None) -> Dict[str, Any]:
        """表单值和已保存的值合并（key 留空表示沿用）。换了地址就不沿用旧 key。"""
        old = self.read()
        base = normalize_base_url(base_url)
        if clear_key:
            key = ""
        else:
            key = (api_key or "").strip() or (old["api_key"] if old["base_url"] == base else "")
        return {
            "base_url": base,
            "api_key": key,
            "timeout": _clamp(timeout or old["timeout"], DEFAULT_TIMEOUT, 5, 300),
            "max_query_chars": _clamp(max_query_chars or old["max_query_chars"], DEFAULT_MAX_QUERY_CHARS, 20, 8000),
        }

    def save(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".kb-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        return self.public()


def query_app(base_url: str, api_key: str, query: str, timeout: int = DEFAULT_TIMEOUT,
              user: str = "testflow") -> Dict[str, Any]:
    """blocking 模式调用一次 Dify 文本生成应用，返回 {answer, resources}。"""
    req = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/completion-messages",
        data=json.dumps({"inputs": {"query": query}, "response_mode": "blocking", "user": user}).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"知识库 HTTP 错误: {exc.code} {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"知识库请求失败: {exc}") from exc
    resources = ((body.get("metadata") or {}).get("retriever_resources") or []) if isinstance(body, dict) else []
    return {"answer": str(body.get("answer") or "").strip(), "resources": [r for r in resources if isinstance(r, dict)]}


def retrieve(query: str, sources: List[Dict[str, str]], cfg: Optional[Dict[str, Any]] = None,
             top_k: int = 6) -> tuple[List[Dict[str, Any]], List[str]]:
    """按顺序查询多个知识库（每个 source = {scope, api_key}），返回 (hits, errors)。

    hits 的字段与本地 RAG 一致：scope / filename / chunk_id / score / text。
    某个知识库失败只记 error，不影响其他来源和本地检索。
    """
    cfg = cfg or KBSettings().read()
    base = cfg.get("base_url", "")
    q = (query or "").strip()[: cfg.get("max_query_chars", DEFAULT_MAX_QUERY_CHARS)]
    hits: List[Dict[str, Any]] = []
    errors: List[str] = []
    if not base or not q:
        return hits, errors
    for src in sources:
        key = (src.get("api_key") or "").strip()
        if not key:
            continue
        try:
            res = query_app(base, key, q, timeout=cfg.get("timeout", DEFAULT_TIMEOUT))
        except Exception as exc:
            errors.append(f"{src.get('label') or src['scope']}: {exc}")
            continue
        items = res["resources"]
        for r in items[:top_k]:
            try:
                score = round(float(r.get("score") or 0), 4)
            except (TypeError, ValueError):
                score = 0.0
            hits.append({
                "scope": src["scope"],
                "filename": str(r.get("document_name") or r.get("dataset_name") or "知识库"),
                "chunk_id": str(r.get("segment_id") or r.get("document_id") or ""),
                "score": score,
                "text": str(r.get("content") or "").strip(),
            })
        if not items and res["answer"]:
            # 应用没开启“引用和归属”时只有 answer，也带上
            hits.append({"scope": src["scope"], "filename": "知识库回答", "chunk_id": "", "score": 0.0, "text": res["answer"]})
    return [h for h in hits if h["text"]], errors
