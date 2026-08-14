from __future__ import annotations

from typing import Any

from sci_colanode_api.services.databases import get_database_schema
from sci_colanode_api.services.field_mapper import map_fields_input
from sci_colanode_api.services.nodes import (
    create_node,
    get_node,
    list_children,
    update_node_attributes,
)
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


async def list_records(
    database_id: str,
    *,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    return await list_children(database_id, node_type="record", client=client)


async def get_record(
    record_id: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    node = await get_node(record_id, client=client)
    if node is None or node.get("type") != "record":
        raise LookupError(f"Record not found: {record_id}")
    return node


async def create_record(
    database_id: str,
    name: str,
    fields: dict[str, Any] | None = None,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    schema = await get_database_schema(database_id, client=client)
    mapped_fields = map_fields_input(schema, fields)
    record_id = await client.generate_id("Record")
    return await create_node(
        node_id=record_id,
        attributes={
            "type": "record",
            "parentId": database_id,
            "databaseId": database_id,
            "name": name,
            "avatar": None,
            "fields": mapped_fields,
        },
        client=client,
    )


async def update_record(
    record_id: str,
    *,
    name: str | None = None,
    fields: dict[str, Any] | None = None,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    current = await get_record(record_id, client=client)
    database_id = current["databaseId"]
    schema = await get_database_schema(database_id, client=client)
    merged_fields = dict(current.get("fields") or {})
    if fields:
        merged_fields.update(map_fields_input(schema, fields))

    attributes = {
        "type": "record",
        "parentId": current["parentId"],
        "databaseId": database_id,
        "name": name if name is not None else current.get("name"),
        "avatar": current.get("avatar"),
        "fields": merged_fields,
    }
    await update_node_attributes(record_id, attributes, client=client)
    return await get_record(record_id, client=client)


async def search_records(
    database_id: str,
    search_query: str,
    *,
    exclude: list[str] | None = None,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    client = client or get_sidecar()
    from sci_colanode_api.services import require_session

    session = await require_session(client)
    payload: dict[str, Any] = {
        "type": "record.search",
        "searchQuery": search_query,
        "userId": session["userId"],
        "databaseId": database_id,
    }
    if exclude:
        payload["exclude"] = exclude
    result = await client.query(payload)
    return list(result or [])


async def delete_record(
    record_id: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    from sci_colanode_api.services.nodes import delete_node

    await get_record(record_id, client=client)
    return await delete_node(record_id, client=client)
