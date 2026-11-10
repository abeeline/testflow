"""LLM 运行时：所有 Agent 的 JSON 生成都走这里。

相比直接 generate + json.loads，多做了几件事：
1) 模板里的 [System] / [User] 段分别作为真正的 system / user 消息发送；
2) 自修复：输出解析失败或不符合 schema 时，把上次输出和具体错误回灌给模型，让它在原答案上修正，
   而不是把同一个提示词盲目重发；
3) 截断识别：finish_reason=length 时抛 LLMTruncated，调用方拆小批次重试（见 run_split_on_truncate）；
4) 顶层是对象的 schema 自动请求 JSON 模式（接口不支持时自动退回）；
5) 记录每个 Agent 的调用次数、修复次数和 token 用量，写进 shared["llm_usage"]，页面可展示。
"""
import json
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.llm_client import LLMTruncated, parse_json_from_llm
from utils.prompt_loader import render_prompt
from utils.schema_validation import validate_jsonschema

DEFAULT_SYSTEM = "You are a senior cellular protocol test engineer. Return strictly valid JSON only."
JSON_RULE = "只输出一个合法 JSON，不要输出 Markdown 代码块以外的解释文字。"
_MAX_ECHO_CHARS = 12000  # 回灌给模型的上次输出最多多少字
_usage_lock = threading.Lock()


def split_prompt(text: str) -> Tuple[str, str]:
    """把模板拆成 (system, user)。没有 [System]/[User] 标记时整段作为 user。"""
    lines = (text or "").splitlines()
    sys_idx = next((i for i, ln in enumerate(lines) if ln.strip() == "[System]"), None)
    user_idx = next((i for i, ln in enumerate(lines) if ln.strip() == "[User]"), None)
    if sys_idx is None or user_idx is None or user_idx < sys_idx:
        return "", text
    system = "\n".join(lines[sys_idx + 1 : user_idx]).strip()
    user = "\n".join(lines[user_idx + 1 :]).strip()
    return system, user


def build_messages(template_name: str, variables: Dict[str, Any]) -> List[Dict[str, str]]:
    system, user = split_prompt(render_prompt(template_name, variables))
    system = (system or DEFAULT_SYSTEM) + "\n" + JSON_RULE
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def record_usage(shared: Dict[str, Any], tag: str, usage: Optional[Dict[str, Any]] = None,
                 repair: bool = False, failed: bool = False) -> None:
    agent = str(tag).split("-Batch")[0]
    usage = usage or {}
    with _usage_lock:
        total = shared.setdefault("llm_usage", {"calls": 0, "repairs": 0, "failures": 0, "prompt_tokens": 0,
                                                "completion_tokens": 0, "by_agent": {}})
        per = total["by_agent"].setdefault(agent, {"calls": 0, "repairs": 0, "failures": 0,
                                                   "prompt_tokens": 0, "completion_tokens": 0})
        for bucket in (total, per):
            bucket["calls"] += 0 if failed else 1
            bucket["repairs"] += 1 if repair else 0
            bucket["failures"] += 1 if failed else 0
            bucket["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            bucket["completion_tokens"] += int(usage.get("completion_tokens") or 0)


def _unwrap_for_schema(data: Any, schema: Dict[str, Any]) -> Any:
    """schema 要数组、模型却包了一层对象（JSON 模式下常见）时，取出唯一的数组字段。"""
    if schema.get("type") == "array" and isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0]
    return data


def _repair_message(error: Exception, truncated: bool) -> str:
    if truncated:
        return ("上一次输出因长度上限被截断，JSON 不完整。请重新输出完整 JSON，并压缩篇幅："
                "说明文字尽量简短，只保留与测试相关的字段和取值，不要省略任何必需字段或条目。")
    return ("上一次输出没有通过校验，错误如下：\n" + str(error)[:1500] +
            "\n请在上一次答案的基础上逐条修正这些问题，保留正确的内容，重新输出完整 JSON（不要只输出修改部分）。")


def generate_json(
    *,
    shared: Dict[str, Any],
    template_name: str,
    variables: Dict[str, Any],
    schema: Dict[str, Any],
    warn_tag: str,
    max_retries: int = 2,
    custom_validator: Optional[Callable[[Any], None]] = None,
    temperature: float = 0.2,
    raise_on_truncate: bool = False,
) -> Any:
    """调用 LLM 生成 JSON 并校验，失败时带错误回灌自修复。全部失败抛 RuntimeError。"""
    client = shared["llm_client"]
    if not client.enabled:
        raise RuntimeError(f"{warn_tag}: LLM未配置")
    run_vars = dict(variables)
    schema_text = json.dumps(schema, ensure_ascii=False)
    run_vars.setdefault("output_schema", schema_text)
    run_vars.setdefault("return_schema", schema_text)
    run_vars.setdefault("last_error", "")
    messages = build_messages(template_name, run_vars)
    json_mode = schema.get("type") == "object"
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            resp = client.chat(messages, temperature=temperature, json_mode=json_mode)
        except Exception as exc:  # 网络/接口错误：原样重试
            last_error = exc
            record_usage(shared, warn_tag, failed=True)
            continue
        record_usage(shared, warn_tag, resp.usage, repair=attempt > 0)
        truncated = resp.finish_reason == "length"
        if truncated and raise_on_truncate:
            raise LLMTruncated(f"{warn_tag}: 输出被截断")
        try:
            data = _unwrap_for_schema(parse_json_from_llm(resp.text), schema)
            validate_jsonschema(data, schema)
            if custom_validator:
                custom_validator(data)
            return data
        except Exception as exc:
            last_error = exc
            messages = messages[:2] + [
                {"role": "assistant", "content": (resp.text or "")[:_MAX_ECHO_CHARS]},
                {"role": "user", "content": _repair_message(exc, truncated)},
            ]
    raise RuntimeError(f"{warn_tag}: LLM生成失败: {last_error}")


def generate_json_or_fallback(*, shared: Dict[str, Any], fallback: Any, warn_tag: str, **kwargs) -> Any:
    """同 generate_json，失败时记一条告警并返回降级结果。"""
    if not shared["llm_client"].enabled:
        shared.setdefault("warnings", []).append(f"{warn_tag}: LLM未配置，使用降级结果")
        return fallback
    try:
        return generate_json(shared=shared, warn_tag=warn_tag, **kwargs)
    except LLMTruncated:
        raise
    except Exception as exc:
        shared.setdefault("warnings", []).append(f"{warn_tag}: 使用降级结果: {exc}")
        return fallback


async def run_split_on_truncate(items: List[Any], worker: Callable[[List[Any]], Any], min_size: int = 1) -> List[Any]:
    """worker(批) 抛 LLMTruncated 时把这一批对半拆开分别重试，直到单条。返回各子批结果列表（按原顺序）。"""
    try:
        return [await worker(items)]
    except LLMTruncated:
        if len(items) <= min_size:
            raise
        mid = len(items) // 2
        left = await run_split_on_truncate(items[:mid], worker, min_size)
        right = await run_split_on_truncate(items[mid:], worker, min_size)
        return left + right


def summarize_usage(usage: Optional[Dict[str, Any]]) -> str:
    if not usage or not usage.get("calls") and not usage.get("failures"):
        return ""
    tokens = int(usage.get("prompt_tokens", 0)) + int(usage.get("completion_tokens", 0))
    parts = [f"LLM 调用 {usage.get('calls', 0)} 次"]
    if usage.get("repairs"):
        parts.append(f"自修复 {usage['repairs']} 次")
    if usage.get("failures"):
        parts.append(f"请求失败 {usage['failures']} 次")
    if tokens:
        parts.append(f"约 {tokens} tokens")
    return "，".join(parts)
