from typing import Any, Dict, Iterable, List

try:
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:  # pragma: no cover
    Draft202012Validator = None


def validate_jsonschema(data: Any, schema: Dict[str, Any]):
    if Draft202012Validator is not None:
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            details = []
            for err in errors[:10]:
                path = ".".join(str(x) for x in err.path) or "$"
                details.append(f"{path}: {err.message}")
            raise ValueError("; ".join(details))
        return

    _validate_fallback(data, schema, "$")


def _validate_fallback(data: Any, schema: Dict[str, Any], path: str):
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected object")
        for req in schema.get("required", []):
            if req not in data:
                raise ValueError(f"{path}: missing required key '{req}'")
        for key, sub in schema.get("properties", {}).items():
            if key in data:
                _validate_fallback(data[key], sub, f"{path}.{key}")
    elif schema_type == "array":
        if not isinstance(data, list):
            raise ValueError(f"{path}: expected array")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(data):
                _validate_fallback(item, item_schema, f"{path}[{idx}]")
    elif schema_type == "string":
        if not isinstance(data, str):
            raise ValueError(f"{path}: expected string")

    if "enum" in schema and data not in schema["enum"]:
        raise ValueError(f"{path}: value '{data}' not in enum")


def require_keys(item: Dict[str, Any], required_keys: Iterable[str], name: str):
    missing = [k for k in required_keys if k not in item]
    if missing:
        raise ValueError(f"{name} missing keys: {missing}")


def validate_list_of_dict(items: Any, required_keys: Iterable[str], name: str):
    if not isinstance(items, list):
        raise ValueError(f"{name} must be a list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{name}[{idx}] must be an object")
        require_keys(item, required_keys, f"{name}[{idx}]")


def ensure_actions_in_vocabulary(testcases: List[Dict[str, Any]], action_vocab: List[str]):
    allowed = set(action_vocab)
    for tc in testcases:
        for step in tc.get("steps", []):
            action = step.get("action")
            if action not in allowed:
                raise ValueError(f"Unknown action '{action}' in tc_id={tc.get('tc_id')}")
