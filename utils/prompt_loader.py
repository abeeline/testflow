from typing import Any, Dict

from utils.paths import prompt_path


def render_prompt(template_name: str, variables: Dict[str, Any]) -> str:
    out = prompt_path(template_name).read_text(encoding="utf-8")
    for k, v in variables.items():
        token = "{" + str(k) + "}"
        out = out.replace(token, v if isinstance(v, str) else str(v))
    return out
