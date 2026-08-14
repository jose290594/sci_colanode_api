from __future__ import annotations

from typing import Any

from sci_colanode_api.services import require_session
from sci_colanode_api.services.nodes import create_node, get_node, update_node_attributes
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


async def create_page(
    parent_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    page_id = await client.generate_id("Page")
    return await create_node(
        node_id=page_id,
        attributes={
            "type": "page",
            "name": name,
            "parentId": parent_id,
            "avatar": None,
        },
        client=client,
    )


async def get_page(
    page_id: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    session = await require_session(client)
    node = await get_node(page_id, client=client)
    if node is None or node.get("type") != "page":
        raise LookupError(f"Page not found: {page_id}")

    document = await client.query(
        {
            "type": "document.get",
            "userId": session["userId"],
            "documentId": page_id,
        }
    )
    return {"page": node, "document": document}


async def update_page_content(
    page_id: str,
    content: str | dict[str, Any],
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    node = await get_node(page_id, client=client)
    if node is None or node.get("type") != "page":
        raise LookupError(f"Page not found: {page_id}")
    return await client.set_document_content(
        user_id=session["userId"],
        document_id=page_id,
        content=content,
    )


async def rename_page(
    page_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    node = await get_node(page_id, client=client)
    if node is None or node.get("type") != "page":
        raise LookupError(f"Page not found: {page_id}")
    await update_node_attributes(
        page_id,
        {
            "type": "page",
            "name": name,
            "parentId": node["parentId"],
            "avatar": node.get("avatar"),
        },
        client=client,
    )
    return await get_page(page_id, client=client)
