from __future__ import annotations

from typing import Any


FIELD_TYPE_TO_VALUE_TYPE = {
    "boolean": "boolean",
    "number": "number",
    "text": "text",
    "string": "string",
    "select": "string",
    "multi_select": "string_array",
    "multiSelect": "string_array",
    "relation": "string_array",
    "created_by": "string",
    "created_at": "string",
    "updated_by": "string",
    "updated_at": "string",
}


def build_field_index(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for field in schema.get("fields") or []:
        field_id = field["id"]
        index[field_id] = field
        name = (field.get("name") or "").strip().lower()
        if name:
            index[name] = field
    return index


def coerce_field_value(field: dict[str, Any], value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and "type" in value and "value" in value:
        return value

    field_type = field.get("type") or "text"
    value_type = FIELD_TYPE_TO_VALUE_TYPE.get(field_type, "text")

    if value_type == "boolean":
        return {"type": "boolean", "value": bool(value)}
    if value_type == "number":
        return {"type": "number", "value": float(value)}
    if value_type == "string_array":
        if isinstance(value, str):
            value = [value]
        return {"type": "string_array", "value": list(value)}
    if value_type == "string":
        return {"type": "string", "value": str(value)}
    return {"type": "text", "value": str(value)}


def map_fields_input(
    schema: dict[str, Any],
    fields: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not fields:
        return {}

    index = build_field_index(schema)
    mapped: dict[str, dict[str, Any]] = {}
    for key, value in fields.items():
        field = index.get(key) or index.get(key.strip().lower())
        if field is None:
            # allow raw field ids even if not in schema snapshot
            if key.endswith("fd") or len(key) > 20:
                mapped[key] = (
                    value
                    if isinstance(value, dict) and "type" in value
                    else {"type": "text", "value": str(value)}
                )
                continue
            raise KeyError(f"Unknown field: {key}")
        mapped[field["id"]] = coerce_field_value(field, value)
    return mapped
