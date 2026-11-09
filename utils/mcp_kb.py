"""知识库检索（MCP 方式）。

每个知识库只需要一个 MCP 地址，例如 http://aifoundry.example.com:8099/mcp/server/<id>/mcp。
“系统设置 → 知识库”里填公共知识库的 MCP 地址，保存在 config/kb-settings.json；
每个项目可以另填自己知识库的 MCP 地址（存在项目里）。检索时同时查“项目知识库 + 公共知识库”。

调用流程（JSON-RPC 2.0，POST 到 MCP 地址）：
    1. tools/list   取第一个工具的名字（结果按地址缓存）
    2. tools/call   arguments = {"query": 带引用提示词的问题}
    3. 把 result.content[].text 拼成回答，并从“引用来源”里解析出资料名称
"""
import json
import os
import re
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
DEFAULT_TOOL_NAME = "3GPP调用"
# 知识库回答带进上下文时每条最多多少字（比本地片段长，因为回答本身就是整理过的内容）
MAX_ANSWER_CHARS = 2000
_lock = threading.Lock()
_tool_cache: Dict[str, str] = {}
_tool_lock = threading.Lock()

CITATION_PROMPT = """请基于知识库内容回答以下问题。回答时务必在末尾列出引用的资料名称和章节编号（如有），格式示例：

📚 引用来源：
- [资料名称] 章节 X.X

用户问题：{query}"""


def normalize_mcp_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    p = urlsplit(raw)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError("请输入完整的 MCP 地址，例如 http://aifoundry.example.com:8099/mcp/server/xxxx/mcp")
    return raw


def _clamp(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return default


class KBSettings:
    """读写公共知识库的 MCP 地址和查询参数。"""

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
            "mcp_url": str(data.get("mcp_url") or ""),
            "timeout": _clamp(data.get("timeout"), DEFAULT_TIMEOUT, 5, 300),
            "max_query_chars": _clamp(data.get("max_query_chars"), DEFAULT_MAX_QUERY_CHARS, 20, 8000),
        }

    def public(self) -> Dict[str, Any]:
        cfg = self.read()
        return {**cfg, "enabled": bool(cfg["mcp_url"])}

    def merged(self, mcp_url: str, timeout: Optional[int] = None,
               max_query_chars: Optional[int] = None) -> Dict[str, Any]:
        old = self.read()
        return {
            "mcp_url": normalize_mcp_url(mcp_url),
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


def _parse_body(raw: str, content_type: str) -> Dict[str, Any]:
    """普通 JSON 或 SSE（data: {...}）两种返回都支持。"""
    text = raw.strip()
    if "text/event-stream" in content_type or text.startswith(("data:", "event:")):
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload.startswith("{"):
                    return json.loads(payload)
        raise RuntimeError("MCP 返回为空")
    return json.loads(text)


def mcp_rpc(mcp_url: str, method: str, params: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    req = urllib.request.Request(
        url=mcp_url,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _parse_body(resp.read().decode("utf-8", errors="replace"), resp.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"知识库 HTTP 错误: {exc.code} {details}") from exc
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"知识库请求失败: {exc}") from exc
    if not isinstance(body, dict):
        raise RuntimeError("知识库返回格式不对")
    if body.get("error"):
        err = body["error"]
        msg = err.get("message") if isinstance(err, dict) else err
        raise RuntimeError(f"知识库返回错误: {msg}")
    return body


def tool_name(mcp_url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    with _tool_lock:
        if mcp_url in _tool_cache:
            return _tool_cache[mcp_url]
    tools = (mcp_rpc(mcp_url, "tools/list", {}, timeout).get("result") or {}).get("tools") or []
    name = str((tools[0] or {}).get("name") or "") if tools and isinstance(tools[0], dict) else ""
    name = name or DEFAULT_TOOL_NAME
    with _tool_lock:
        _tool_cache[mcp_url] = name
    return name


_CITE_HEAD = re.compile(r"引用来源")
_CITE_LINE = re.compile(r"^\s*(?:[-*•·]|\d+[.、)])\s*(.+?)\s*$")


def parse_citations(text: str) -> List[str]:
    """从回答末尾的“📚 引用来源：”列表里取出资料名称（含章节）。"""
    lines = (text or "").splitlines()
    start = next((i for i, l in enumerate(lines) if _CITE_HEAD.search(l)), -1)
    if start < 0:
        return []
    out: List[str] = []
    for line in lines[start + 1:]:
        m = _CITE_LINE.match(line)
        if not m:
            if line.strip():
                break
            continue
        item = re.sub(r"\[([^\]]+)\]", r"\1", m.group(1)).strip()
        if item and item not in out:
            out.append(item)
    return out


def query_kb(mcp_url: str, query: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """调用一次知识库，返回 {answer, citations}。"""
    name = tool_name(mcp_url, timeout)
    body = mcp_rpc(mcp_url, "tools/call", {"name": name, "arguments": {"query": CITATION_PROMPT.format(query=query)}}, timeout)
    result = body.get("result") or {}
    parts = [str(c.get("text") or "") for c in (result.get("content") or []) if isinstance(c, dict)]
    answer = "\n".join(p for p in parts if p).strip()
    if result.get("isError"):
        raise RuntimeError(f"知识库工具报错: {answer[:300] or '未知错误'}")
    return {"answer": answer, "citations": parse_citations(answer)}


def answer_to_hit(scope: str, res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """把一次回答转成与本地 RAG 一致的片段格式：scope / filename / chunk_id / score / text。"""
    if not res.get("answer"):
        return None
    cites = res.get("citations") or []
    return {
        "scope": scope,
        "filename": "；".join(cites[:3]) or "知识库回答",
        "chunk_id": "",
        "score": 1.0,
        "text": res["answer"],
        "citations": cites,
        "max_chars": MAX_ANSWER_CHARS,
    }


def retrieve(query: str, sources: List[Dict[str, str]], cfg: Optional[Dict[str, Any]] = None) -> tuple[List[Dict[str, Any]], List[str]]:
    """按顺序查询多个知识库（每个 source = {scope, label, mcp_url}），返回 (hits, errors)。

    某个知识库失败只记 error，不影响其他来源和本地检索。
    """
    cfg = cfg or KBSettings().read()
    q = (query or "").strip()[: cfg.get("max_query_chars", DEFAULT_MAX_QUERY_CHARS)]
    hits: List[Dict[str, Any]] = []
    errors: List[str] = []
    if not q:
        return hits, errors
    for src in sources:
        url = (src.get("mcp_url") or "").strip()
        if not url:
            continue
        try:
            res = query_kb(url, q, timeout=cfg.get("timeout", DEFAULT_TIMEOUT))
        except Exception as exc:
            errors.append(f"{src.get('label') or src['scope']}: {exc}")
            continue
        hit = answer_to_hit(src["scope"], res)
        if hit:
            hits.append(hit)
    return hits, errors
