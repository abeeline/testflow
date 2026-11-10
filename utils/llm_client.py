"""OpenAI 兼容的 LLM 客户端。

配置在网页“系统设置 → 大模型”里填写，保存在 config/llm-settings.json。
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

SETTINGS_PATH = CONFIG_DIR / "llm-settings.json"
DEFAULT_TIMEOUT = 120
_lock = threading.Lock()


def normalize_api_base(value: str) -> str:
    raw = (value or "").strip().rstrip("/")
    if not raw:
        return ""
    p = urlsplit(raw)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("请输入完整的 http(s) 接口地址，例如 https://api.openai.com/v1")
    if raw.endswith("/chat/completions"):
        raw = raw[: -len("/chat/completions")]
    return raw


class LLMSettings:
    """读写网页配置的 LLM 参数。接口只回显 key 是否已配置，不回显 key 本身。"""

    def __init__(self, path: Path = SETTINGS_PATH):
        self.path = Path(path)

    def read(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8")) or {}
            except Exception:
                data = {}
        try:
            timeout = int(data.get("timeout") or DEFAULT_TIMEOUT)
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT
        return {
            "api_base": str(data.get("api_base") or ""),
            "api_key": str(data.get("api_key") or ""),
            "model": str(data.get("model") or ""),
            "timeout": max(10, min(timeout, 600)),
        }

    def public(self) -> Dict[str, Any]:
        cfg = self.read()
        return {
            "api_base": cfg["api_base"],
            "model": cfg["model"],
            "timeout": cfg["timeout"],
            "key_configured": bool(cfg["api_key"]),
            "enabled": bool(cfg["api_base"] and cfg["api_key"] and cfg["model"]),
        }

    def merged(self, api_base: str, model: str, api_key: str = "", clear_key: bool = False,
               timeout: Optional[int] = None) -> Dict[str, Any]:
        """把表单值和已保存的值合并（key 留空表示沿用）。换了地址就不沿用旧 key。"""
        old = self.read()
        base = normalize_api_base(api_base)
        if clear_key:
            key = ""
        else:
            key = (api_key or "").strip() or (old["api_key"] if old["api_base"] == base else "")
        return {
            "api_base": base,
            "api_key": key,
            "model": (model or "").strip(),
            "timeout": max(10, min(int(timeout or old["timeout"]), 600)),
        }

    def save(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".llm-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        return self.public()


class LLMTruncated(RuntimeError):
    """模型输出因长度上限被截断（finish_reason=length）。调用方应拆小批次重试，而不是原样重发。"""


class LLMResponse:
    def __init__(self, text: str, finish_reason: str = "", usage: Optional[Dict[str, Any]] = None):
        self.text = text
        self.finish_reason = finish_reason or ""
        self.usage = usage or {}


# 记住哪些接口不支持 response_format=json_object，避免每次都先失败一次
_JSON_MODE_UNSUPPORTED: set = set()


class LLMClient:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or LLMSettings().read()
        self.api_base = str(cfg.get("api_base") or "").rstrip("/")
        self.api_key = str(cfg.get("api_key") or "")
        self.model = str(cfg.get("model") or "")
        self.timeout = int(cfg.get("timeout") or DEFAULT_TIMEOUT)

    @property
    def enabled(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req = urllib.request.Request(
            url=f"{self.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")[:500]
            err = RuntimeError(f"LLM HTTP 错误: {exc.code} {details}")
            err.status = exc.code  # type: ignore[attr-defined]
            raise err from exc
        except Exception as exc:
            raise RuntimeError(f"LLM 请求失败: {exc}") from exc

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """多轮对话调用。json_mode=True 时请求 response_format=json_object，接口不支持则自动退回普通模式。"""
        if not self.enabled:
            raise RuntimeError("大模型未配置，请在“系统设置 → 大模型”中填写接口地址、API Key 和模型名称。")
        payload: Dict[str, Any] = {"model": self.model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        mode_key = f"{self.api_base}|{self.model}"
        use_json = json_mode and mode_key not in _JSON_MODE_UNSUPPORTED
        if use_json:
            payload["response_format"] = {"type": "json_object"}
        try:
            body = self._post(payload)
        except RuntimeError as exc:
            if not use_json or getattr(exc, "status", 0) not in (400, 404, 415, 422, 500, 501):
                raise
            _JSON_MODE_UNSUPPORTED.add(mode_key)
            payload.pop("response_format", None)
            body = self._post(payload)
        try:
            choice = body["choices"][0]
            text = (choice["message"]["content"] or "").strip()
        except Exception as exc:
            raise RuntimeError(f"LLM 响应解析失败: {str(body)[:500]}") from exc
        return LLMResponse(text, str(choice.get("finish_reason") or ""), body.get("usage") or {})

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens).text

    def generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        text = self.generate(system_prompt, user_prompt)
        return parse_json_from_llm(text)


def _balanced_blocks(text: str) -> List[str]:
    """找出文本里所有最外层的 {...} / [...] 片段（跳过字符串内的括号）。"""
    out, stack, start, in_str, esc = [], [], -1, False, False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            if not stack:
                start = i
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            if ch != stack[-1]:
                stack, start = [], -1
                continue
            stack.pop()
            if not stack and start >= 0:
                out.append(text[start : i + 1])
                start = -1
    return out


def _loads_lenient(candidate: str) -> Any:
    try:
        return json.loads(candidate)
    except Exception:
        pass
    # 常见小毛病：结尾多余逗号
    fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
    return json.loads(fixed)


def parse_json_from_llm(text: str) -> Any:
    # 兼容推理模型输出的 <think>…</think> 段落
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    candidates = fenced + [text]
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            return _loads_lenient(candidate)
        except Exception:
            continue
    blocks = sorted(_balanced_blocks(text), key=len, reverse=True)
    for block in blocks:
        try:
            return _loads_lenient(block)
        except Exception:
            continue
    raise ValueError(f"No valid JSON found in LLM output: {text[:500]}")
