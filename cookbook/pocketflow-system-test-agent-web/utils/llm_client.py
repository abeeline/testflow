import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional


class LLMClient:
    def __init__(self):
        _load_local_env()
        self.api_base = os.getenv("LLM_API_BASE", "").rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "")

    @property
    def enabled(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("LLM config is missing. Set LLM_API_BASE, LLM_API_KEY, LLM_MODEL.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = f"{self.api_base}/chat/completions"
        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM HTTP error: {exc.code} {details}") from exc
        except Exception as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        try:
            return body["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise RuntimeError(f"LLM response parse failed: {body}") from exc

    def generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        text = self.generate(system_prompt, user_prompt)
        return parse_json_from_llm(text)


def parse_json_from_llm(text: str) -> Any:
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    candidates = fenced + [text]
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            return json.loads(candidate)
        except Exception:
            continue
    raise ValueError(f"No valid JSON found in LLM output: {text[:500]}")


def _load_local_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
