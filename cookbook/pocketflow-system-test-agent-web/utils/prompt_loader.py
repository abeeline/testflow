from pathlib import Path
from typing import Any, Dict


_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def render_prompt(template_name: str, variables: Dict[str, Any]) -> str:
    p = _PROMPT_DIR / template_name
    raw = p.read_text(encoding="utf-8")
    out = raw
    for k, v in variables.items():
        token = "{" + str(k) + "}"
        out = out.replace(token, v if isinstance(v, str) else str(v))
    return out
