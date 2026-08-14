from __future__ import annotations

from typing import Any

from sci_colanode_api.services.nodes import (
    create_node,
    get_node,
    list_nodes,
    update_node_attributes,
)
from sci_colanode_api.services import mutation_ok, require_session
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


async def list_spaces(client: SidecarClient | None = None) -> list[dict[str, Any]]:
    return await list_nodes(node_type="space", client=client)


async def create_space(
    name: str,
    *,
    description: str | None = None,
    visibility: str = "private",
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    session = await client.session() or await client.ensure_auth()
    space_id = await client.generate_id("Space")
    page_id = await client.generate_id("Page")

    space = await create_node(
        node_id=space_id,
        attributes={
            "type": "space",
            "name": name,
            "description": description,
            "avatar": None,
            "collaborators": {session["userId"]: "admin"},
            "visibility": visibility,
        },
        client=client,
    )

    await create_node(
        node_id=page_id,
        attributes={
            "type": "page",
            "name": "Home",
            "parentId": space_id,
            "avatar": None,
        },
        client=client,
    )
    return space


async def rename_space(
    space_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    return await update_space(space_id, name=name, client=client)


async def update_space(
    space_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    visibility: str | None = None,
    client: SidecarClient | None = None,
) -> Any:
    node = await get_node(space_id, client=client)
    if node is None or node.get("type") != "space":
        raise LookupError(f"Space not found: {space_id}")
    attributes = {
        "type": "space",
        "name": name if name is not None else node.get("name"),
        "description": description if description is not None else node.get("description"),
        "avatar": node.get("avatar"),
        "collaborators": node.get("collaborators") or {},
        "visibility": visibility if visibility is not None else (node.get("visibility") or "private"),
        "children": node.get("children"),
    }
    await update_node_attributes(space_id, attributes, client=client)
    return await get_node(space_id, client=client)


async def reorder_space_child(
    space_id: str,
    child_id: str,
    after: str | None = None,
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "space.child.reorder",
            "userId": session["userId"],
            "spaceId": space_id,
            "childId": child_id,
            "after": after,
        }
    )
    return mutation_ok(result)
