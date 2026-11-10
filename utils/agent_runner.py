"""兼容旧接口：内部统一走 core.llm 的运行时（system/user 拆分、自修复、截断识别、用量统计）。"""
from typing import Any, Callable, Dict, Optional

from core.llm import generate_json, generate_json_or_fallback, record_usage, split_prompt
from utils.prompt_loader import render_prompt


def run_json_agent_with_retry(
    *,
    shared: Dict[str, Any],
    template_name: str,
    variables: Dict[str, Any],
    schema: Dict[str, Any],
    fallback: Any,
    warn_tag: str,
    max_retries: int = 2,
    custom_validator: Optional[Callable[[Any], None]] = None,
) -> Any:
    return generate_json_or_fallback(
        shared=shared, fallback=fallback, warn_tag=warn_tag, template_name=template_name,
        variables=variables, schema=schema, max_retries=max_retries, custom_validator=custom_validator,
    )


def run_json_agent_strict_with_retry(
    *,
    shared: Dict[str, Any],
    template_name: str,
    variables: Dict[str, Any],
    schema: Dict[str, Any],
    warn_tag: str,
    max_retries: int = 2,
    custom_validator: Optional[Callable[[Any], None]] = None,
) -> Any:
    return generate_json(
        shared=shared, template_name=template_name, variables=variables, schema=schema,
        warn_tag=warn_tag, max_retries=max_retries, custom_validator=custom_validator,
    )


def run_text_agent(
    *,
    shared: Dict[str, Any],
    template_name: str,
    variables: Dict[str, Any],
    fallback: str,
    warn_tag: str,
) -> str:
    client = shared["llm_client"]
    if not client.enabled:
        shared.setdefault("warnings", []).append(f"{warn_tag}: LLM未配置，使用降级结果")
        return fallback
    try:
        system, user = split_prompt(render_prompt(template_name, variables))
        resp = client.chat([{"role": "system", "content": system or "Return practical content only."},
                            {"role": "user", "content": user}])
        record_usage(shared, warn_tag, resp.usage)
        return resp.text
    except Exception as exc:
        shared.setdefault("warnings", []).append(f"{warn_tag}: LLM调用失败，使用降级结果: {exc}")
        return fallback
