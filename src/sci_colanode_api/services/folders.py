from __future__ import annotations

from typing import Any

from sci_colanode_api.services.nodes import create_node, get_node, update_node_attributes
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


async def create_folder(
    parent_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    folder_id = await client.generate_id("Folder")
    return await create_node(
        node_id=folder_id,
        attributes={
            "type": "folder",
            "name": name,
            "parentId": parent_id,
            "avatar": None,
        },
        client=client,
    )


async def rename_folder(
    folder_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    node = await get_node(folder_id, client=client)
    if node is None or node.get("type") != "folder":
        raise LookupError(f"Folder not found: {folder_id}")
    return await update_node_attributes(
        folder_id,
        {
            "type": "folder",
            "name": name,
            "parentId": node["parentId"],
            "avatar": node.get("avatar"),
        },
        client=client,
    )
