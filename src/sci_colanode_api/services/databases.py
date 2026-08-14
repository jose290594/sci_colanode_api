from __future__ import annotations

from typing import Any

from sci_colanode_api.services.nodes import (
    create_node,
    get_node,
    list_children,
    update_node_attributes,
)
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar

ALLOWED_FIELD_TYPES = {
    "boolean",
    "collaborator",
    "created_at",
    "created_by",
    "date",
    "email",
    "file",
    "multi_select",
    "number",
    "phone",
    "select",
    "text",
    "relation",
    "updated_at",
    "updated_by",
    "url",
}


def _database_attributes(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "database",
        "name": node.get("name"),
        "avatar": node.get("avatar"),
        "parentId": node.get("parentId"),
        "fields": dict(node.get("fields") or {}),
        "nameField": node.get("nameField"),
        "locked": node.get("locked"),
    }


async def _require_database(
    database_id: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    node = await get_node(database_id, client=client)
    if node is None or node.get("type") != "database":
        raise LookupError(f"Database not found: {database_id}")
    return node


async def list_databases(
    space_id: str | None = None,
    *,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    from sci_colanode_api.services.nodes import list_nodes

    return await list_nodes(parent_id=space_id, node_type="database", client=client)


async def get_database_schema(
    database_id: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    node = await _require_database(database_id, client=client)
    fields = node.get("fields") or {}
    return {
        "id": node["id"],
        "name": node.get("name"),
        "parentId": node.get("parentId"),
        "nameField": node.get("nameField"),
        "fields": [
            {
                "id": field_id,
                "name": field.get("name"),
                "type": field.get("type"),
                "index": field.get("index"),
                "options": field.get("options"),
                "databaseId": field.get("databaseId"),
            }
            for field_id, field in fields.items()
            if isinstance(field, dict)
        ],
        "rawFields": fields,
    }


async def create_database(
    space_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    database_id = await client.generate_id("Database")
    field_id = await client.generate_id("Field")
    view_id = await client.generate_id("DatabaseView")
    field_index = await client.generate_index()
    view_index = await client.generate_index()

    database = await create_node(
        node_id=database_id,
        attributes={
            "type": "database",
            "name": name,
            "parentId": space_id,
            "avatar": None,
            "fields": {
                field_id: {
                    "id": field_id,
                    "type": "text",
                    "index": field_index,
                    "name": "Comment",
                }
            },
        },
        client=client,
    )
    await create_node(
        node_id=view_id,
        attributes={
            "type": "database_view",
            "name": "Default",
            "parentId": database_id,
            "layout": "table",
            "index": view_index,
        },
        client=client,
    )
    return database


async def add_field(
    database_id: str,
    name: str,
    field_type: str,
    *,
    relation_database_id: str | None = None,
    options: list[dict[str, Any]] | None = None,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    if field_type not in ALLOWED_FIELD_TYPES:
        raise KeyError(f"Unsupported field type: {field_type}")
    if field_type == "relation" and not relation_database_id:
        raise KeyError("relation_database_id is required for relation fields")

    node = await _require_database(database_id, client=client)
    fields = dict(node.get("fields") or {})
    max_index = None
    for field in fields.values():
        if isinstance(field, dict) and field.get("index"):
            idx = str(field["index"])
            if max_index is None or idx > max_index:
                max_index = idx
    field_id = await client.generate_id("Field")
    index = await client.generate_index(previous=max_index)
    new_field: dict[str, Any] = {
        "id": field_id,
        "type": field_type,
        "name": name,
        "index": index,
    }
    if field_type == "relation":
        new_field["databaseId"] = relation_database_id
    if field_type in {"select", "multi_select"} and options:
        option_map: dict[str, Any] = {}
        prev = None
        for opt in options:
            opt_id = await client.generate_id("SelectOption")
            opt_index = await client.generate_index(previous=prev)
            prev = opt_index
            option_map[opt_id] = {
                "id": opt_id,
                "name": opt.get("name") or "Option",
                "color": opt.get("color") or "gray",
                "index": opt_index,
            }
        new_field["options"] = option_map
    fields[field_id] = new_field
    attrs = _database_attributes(node)
    attrs["fields"] = fields
    await update_node_attributes(database_id, attrs, client=client)
    schema = await get_database_schema(database_id, client=client)
    return {"field_id": field_id, "schema": schema}


async def update_field(
    database_id: str,
    field_id: str,
    *,
    name: str | None = None,
    options: dict[str, Any] | None = None,
    relation_database_id: str | None = None,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    node = await _require_database(database_id, client=client)
    fields = dict(node.get("fields") or {})
    field = fields.get(field_id)
    if not isinstance(field, dict):
        raise LookupError(f"Field not found: {field_id}")
    if name is not None:
        field["name"] = name
    if options is not None:
        field["options"] = options
    if relation_database_id is not None:
        field["databaseId"] = relation_database_id
    fields[field_id] = field
    attrs = _database_attributes(node)
    attrs["fields"] = fields
    await update_node_attributes(database_id, attrs, client=client)
    return await get_database_schema(database_id, client=client)


async def delete_field(
    database_id: str,
    field_id: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    node = await _require_database(database_id, client=client)
    fields = dict(node.get("fields") or {})
    if field_id not in fields:
        raise LookupError(f"Field not found: {field_id}")
    del fields[field_id]
    attrs = _database_attributes(node)
    attrs["fields"] = fields
    await update_node_attributes(database_id, attrs, client=client)
    return await get_database_schema(database_id, client=client)


async def list_views(
    database_id: str,
    *,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    return await list_children(database_id, node_type="database_view", client=client)


async def create_view(
    database_id: str,
    name: str,
    layout: str = "table",
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    await _require_database(database_id, client=client)
    if layout not in {"table", "board", "calendar"}:
        raise KeyError("layout must be table, board or calendar")
    views = await list_views(database_id, client=client)
    max_index = None
    for view in views:
        idx = view.get("index")
        if idx and (max_index is None or str(idx) > max_index):
            max_index = str(idx)
    view_id = await client.generate_id("DatabaseView")
    index = await client.generate_index(previous=max_index)
    return await create_node(
        node_id=view_id,
        attributes={
            "type": "database_view",
            "name": name or layout.title(),
            "parentId": database_id,
            "layout": layout,
            "index": index,
        },
        client=client,
    )
