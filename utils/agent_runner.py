import json
from typing import Any, Callable, Dict, Optional

from utils.prompt_loader import render_prompt
from utils.schema_validation import validate_jsonschema


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
    client = shared["llm_client"]
    schema_text = json.dumps(schema, ensure_ascii=False)
    last_error = None

    for attempt in range(max_retries + 1):
        run_vars = dict(variables)
        run_vars.setdefault("output_schema", schema_text)
        if last_error:
            run_vars["last_error"] = str(last_error)

        try:
            prompt = render_prompt(template_name, run_vars)
        except Exception as exc:
            last_error = exc
            continue

        if not client.enabled:
            shared.setdefault("warnings", []).append(f"{warn_tag}: LLM未配置，使用降级结果")
            return fallback

        try:
            data = client.generate_json("Return strictly valid JSON only.", prompt)
            validate_jsonschema(data, schema)
            if custom_validator:
                custom_validator(data)
            return data
        except Exception as exc:
            last_error = exc

    shared.setdefault("warnings", []).append(f"{warn_tag}: JSON schema校验失败，使用降级结果: {last_error}")
    return fallback


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
    client = shared["llm_client"]
    schema_text = json.dumps(schema, ensure_ascii=False)
    last_error = None

    for _ in range(max_retries + 1):
        run_vars = dict(variables)
        run_vars.setdefault("output_schema", schema_text)
        if last_error:
            run_vars["last_error"] = str(last_error)
        try:
            prompt = render_prompt(template_name, run_vars)
        except Exception as exc:
            last_error = exc
            continue

        if not client.enabled:
            raise RuntimeError(f"{warn_tag}: LLM未配置，无法执行严格生成")

        try:
            data = client.generate_json("Return strictly valid JSON only.", prompt)
            validate_jsonschema(data, schema)
            if custom_validator:
                custom_validator(data)
            return data
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"{warn_tag}: LLM严格生成失败: {last_error}")


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
        prompt = render_prompt(template_name, variables)
        return client.generate("Return practical content only.", prompt)
    except Exception as exc:
        shared.setdefault("warnings", []).append(f"{warn_tag}: LLM调用失败，使用降级结果: {exc}")
        return fallback
