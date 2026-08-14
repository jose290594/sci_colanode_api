from __future__ import annotations

from typing import Any

from sci_colanode_api.services import mutation_ok, require_session
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


def _filters(
    *,
    parent_id: str | None = None,
    node_type: str | list[str] | None = None,
    node_id: str | None = None,
) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    if parent_id is not None:
        filters.append({"field": ["parentId"], "operator": "eq", "value": parent_id})
    if node_id is not None:
        filters.append({"field": ["id"], "operator": "eq", "value": node_id})
    if node_type is not None:
        if isinstance(node_type, list):
            filters.append({"field": ["type"], "operator": "in", "value": node_type})
        else:
            filters.append({"field": ["type"], "operator": "eq", "value": node_type})
    return filters


async def list_nodes(
    *,
    parent_id: str | None = None,
    node_type: str | list[str] | None = None,
    limit: int | None = None,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    client = client or get_sidecar()
    session = await require_session(client)
    query: dict[str, Any] = {
        "type": "node.list",
        "userId": session["userId"],
        "filters": _filters(parent_id=parent_id, node_type=node_type),
        "sorts": [],
    }
    if limit is not None:
        query["limit"] = limit
    result = await client.query(query)
    return list(result or [])


async def get_node(
    node_id: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any] | None:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.query(
        {
            "type": "node.list",
            "userId": session["userId"],
            "filters": _filters(node_id=node_id),
            "sorts": [],
            "limit": 1,
        }
    )
    nodes = list(result or [])
    return nodes[0] if nodes else None


async def list_children(
    parent_id: str,
    *,
    node_type: str | list[str] | None = None,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    return await list_nodes(parent_id=parent_id, node_type=node_type, client=client)


async def get_tree(
    root_id: str,
    *,
    depth: int = 3,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    root = await get_node(root_id, client=client)
    if root is None:
        raise LookupError(f"Node not found: {root_id}")

    async def walk(node: dict[str, Any], remaining: int) -> dict[str, Any]:
        item = {"node": node, "children": []}
        if remaining <= 0:
            return item
        children = await list_children(node["id"], client=client)
        item["children"] = [await walk(child, remaining - 1) for child in children]
        return item

    return await walk(root, depth)


async def delete_node(
    node_id: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "node.delete",
            "userId": session["userId"],
            "nodeId": node_id,
        }
    )
    return mutation_ok(result)


async def update_node_attributes(
    node_id: str,
    attributes: dict[str, Any],
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "node.update",
            "userId": session["userId"],
            "nodeId": node_id,
            "attributes": attributes,
        }
    )
    return mutation_ok(result)


async def create_node(
    *,
    node_id: str,
    attributes: dict[str, Any],
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "node.create",
            "userId": session["userId"],
            "nodeId": node_id,
            "attributes": attributes,
        }
    )
    mutation_ok(result)
    node = await get_node(node_id, client=client)
    if node is None:
        return {"id": node_id, **attributes}
    return node


async def rename_node(
    node_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    node = await get_node(node_id, client=client)
    if node is None:
        raise LookupError(f"Node not found: {node_id}")
    node_type = node.get("type")
    if node_type == "space":
        from sci_colanode_api.services.spaces import update_space

        updated = await update_space(node_id, name=name, client=client)
        return updated if isinstance(updated, dict) else node
    attributes: dict[str, Any] = {"type": node_type, "name": name}
    if node.get("parentId"):
        attributes["parentId"] = node["parentId"]
    if "avatar" in node:
        attributes["avatar"] = node.get("avatar")
    if node_type == "database":
        attributes["fields"] = node.get("fields") or {}
        attributes["nameField"] = node.get("nameField")
        attributes["locked"] = node.get("locked")
    elif node_type == "channel":
        pass
    elif node_type == "folder":
        pass
    elif node_type == "page":
        pass
    elif node_type == "database_view":
        attributes["layout"] = node.get("layout")
        attributes["index"] = node.get("index")
        attributes["fields"] = node.get("fields")
        attributes["filters"] = node.get("filters")
        attributes["sorts"] = node.get("sorts")
    elif node_type == "record":
        from sci_colanode_api.services.records import update_record

        return await update_record(node_id, name=name, client=client)
    else:
        # keep extra known attributes
        for key in ("description", "visibility", "collaborators", "children"):
            if key in node:
                attributes[key] = node.get(key)
    await update_node_attributes(node_id, attributes, client=client)
    updated = await get_node(node_id, client=client)
    if updated is None:
        raise LookupError(f"Node not found after rename: {node_id}")
    return updated
