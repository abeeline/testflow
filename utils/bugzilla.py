"""只读 Bugzilla 接入：按编号读取研发需求 / Bug 的标题、状态和评论，作为测试需求输入。

兼容 Bugzilla 5.x：配置了 API Key 时走 JSON-RPC（避免把 key 放进 URL），否则走匿名 REST。
"""
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, unquote, urlencode, urlsplit, urlunsplit

MAX_BUGS = 20
MAX_COMMENTS = 40
MAX_COMMENT_CHARS = 4000
MAX_RESPONSE_BYTES = 4_000_000


def tokens(text: str) -> List[str]:
    return list(dict.fromkeys(s.strip() for s in re.split(r"[,，\s]+", text or "") if s.strip()))


def normalize_url(value: str) -> str:
    p = urlsplit((value or "").strip())
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("请输入完整的 Bugzilla http(s) 地址，不包含账号、查询参数或锚点。")
    path = p.path.rstrip("/")
    if path.endswith("/rest"):
        path = path[:-5]
    if path.endswith("/show_bug.cgi"):
        raise ValueError("请填写 Bugzilla 站点地址，而不是单个 Bug 页面。")
    return urlunsplit((p.scheme, p.netloc, path, "", ""))


class BugzillaSettings:
    def __init__(self, path: Path):
        self.path = Path(path)

    def read(self) -> Dict[str, str]:
        if not self.path.exists():
            return {"url": "", "api_key": ""}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"url": "", "api_key": ""}
        return {"url": str(data.get("url") or ""), "api_key": str(data.get("api_key") or "")}

    def public(self) -> Dict[str, Any]:
        cfg = self.read()
        return {"url": cfg["url"], "key_configured": bool(cfg["api_key"])}

    def save(self, url: str, api_key: str = "", clear_key: bool = False) -> Dict[str, Any]:
        url = normalize_url(url)
        old = self.read()
        # 地址变了就不沿用旧 key，避免把凭据发到别的站点。
        key = "" if clear_key else (api_key or "").strip() or (old["api_key"] if old["url"] == url else "")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".bugzilla-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"url": url, "api_key": key}, f)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return self.public()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # 不跟随重定向，防止凭据被转发到其他主机
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _request(cfg: Dict[str, str], path: str, params: Optional[List[Tuple[str, str]]] = None, timeout: int = 20) -> Dict[str, Any]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if cfg["api_key"]:
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "bug":
            op, args = "Bug.get", {"ids": [unquote(parts[1])]}
        elif len(parts) == 3 and parts[0] == "bug" and parts[2] == "comment":
            op, args = "Bug.comments", {"ids": [unquote(parts[1])]}
        elif path == "version":
            op, args = "Bugzilla.version", {}
        else:
            raise ValueError("不支持的只读 Bugzilla 查询。")
        args["api_key"] = cfg["api_key"]
        body = json.dumps({"method": op, "params": [args], "id": "testflow-read"}).encode("utf-8")
        req = urllib.request.Request(cfg["url"] + "/jsonrpc.cgi", data=body, headers=headers, method="POST")
    else:
        url = cfg["url"] + "/rest/" + path + (("?" + urlencode(params)) if params else "")
        req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with _opener.open(req, timeout=timeout) as resp:
            raw = resp.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise ValueError("无访问权限，请检查 API Key 和 Bug 权限。") from None
        if exc.code == 404:
            raise ValueError("未找到 Bug 或 API 接口，请检查地址与编号。") from None
        raise ValueError(f"Bugzilla 返回 HTTP {exc.code}，请检查站点配置。") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("无法连接 Bugzilla，请检查网络、证书和地址。") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Bug 内容过大。")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Bugzilla 返回的不是 JSON，请检查地址。") from None
    if not isinstance(data, dict) or data.get("error"):
        msg = (data.get("error") or {}).get("message") if isinstance(data, dict) and isinstance(data.get("error"), dict) else ""
        msg = str(msg or "Bugzilla 查询失败，请检查编号、密钥和访问权限。")
        if cfg["api_key"]:
            msg = msg.replace(cfg["api_key"], "***")
        raise ValueError(msg)
    if cfg["api_key"]:
        data = data.get("result")
        if not isinstance(data, dict):
            raise ValueError("Bugzilla JSON-RPC 响应格式不兼容。")
    return data


def _filter_comments(comments: List[Dict[str, Any]], excluded: str) -> Tuple[List[Dict[str, Any]], int]:
    words = [w.casefold() for w in tokens(excluded)]
    kept, removed = [], 0
    for c in sorted(comments, key=lambda c: c.get("count", 0)):
        creator = str(c.get("creator") or c.get("author") or "")
        if words and any(w in creator.casefold() for w in words):
            removed += 1
            continue
        text = str(c.get("text") or "")
        if len(text) > MAX_COMMENT_CHARS:
            text = text[:MAX_COMMENT_CHARS] + "\n[内容截断]"
        kept.append({"number": c.get("count"), "author": creator, "time": c.get("creation_time") or c.get("time"), "text": text})
    if len(kept) > MAX_COMMENTS:  # 保留首条描述和最近的讨论
        kept = kept[:1] + kept[-(MAX_COMMENTS - 1):]
    return kept, removed


def fetch_bugs(ids: str, cfg: Dict[str, str], excluded_authors: str = "") -> List[Dict[str, Any]]:
    identifiers = tokens(ids)
    if not identifiers or len(identifiers) > MAX_BUGS or any(not re.fullmatch(r"[\w.-]{1,120}", i) for i in identifiers):
        raise ValueError(f"请填写 1–{MAX_BUGS} 个 Bug 编号或别名，以逗号分隔，不要填写网址。")
    if not cfg.get("url"):
        raise ValueError("请先保存 Bugzilla 地址（和 API Key）。")
    results = []
    for ident in identifiers:
        try:
            bug = _request(cfg, "bug/" + quote(ident, safe=""))["bugs"][0]
            actual = str(bug["id"])
            comments = _request(cfg, f"bug/{quote(actual, safe='')}/comment")["bugs"][actual]["comments"]
            kept, removed = _filter_comments(comments, excluded_authors)
            results.append({
                "requested_id": ident,
                "id": actual,
                "status": "ok",
                "url": cfg["url"] + "/show_bug.cgi?id=" + quote(actual),
                "title": bug.get("summary", ""),
                "bug_status": bug.get("status"),
                "resolution": bug.get("resolution"),
                "product": bug.get("product"),
                "component": bug.get("component"),
                "version": bug.get("version"),
                "severity": bug.get("severity"),
                "priority": bug.get("priority"),
                "last_change_time": bug.get("last_change_time"),
                "comments": kept,
                "excluded_count": removed,
            })
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            results.append({"requested_id": ident, "status": "error",
                            "error": str(exc) if isinstance(exc, ValueError) else "Bugzilla 响应格式不兼容。"})
    return results


def bugs_to_requirement_text(bugs: List[Dict[str, Any]]) -> str:
    """把读取到的 Bug 整理成需求描述文本，保留 Bug 编号便于追溯。"""
    blocks = []
    for b in bugs:
        if b.get("status") != "ok":
            continue
        head = f"【需求来源 BZ#{b['id']}】{b.get('title', '')}"
        meta = " | ".join(x for x in [
            f"Product: {b.get('product')}" if b.get("product") else "",
            f"Component: {b.get('component')}" if b.get("component") else "",
            f"状态: {b.get('bug_status')}" if b.get("bug_status") else "",
            f"链接: {b.get('url')}",
        ] if x)
        comments = b.get("comments") or []
        desc = comments[0]["text"].strip() if comments else ""
        lines = [head, meta]
        if desc:
            lines.append("描述:\n" + desc)
        for c in comments[1:]:
            text = (c.get("text") or "").strip()
            if text:
                lines.append(f"评论#{c.get('number')} ({c.get('author')}):\n{text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
