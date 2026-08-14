from __future__ import annotations

from typing import Any

from sci_colanode_api.services.nodes import create_node, delete_node, get_node, list_children
from sci_colanode_api.services import mutation_ok, require_session
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


def plain_text_to_tiptap(text: str) -> dict[str, Any]:
    paragraph: dict[str, Any] = {"type": "paragraph"}
    if text:
        paragraph["content"] = [{"type": "text", "text": text}]
    return {"type": "doc", "content": [paragraph]}


async def create_channel(
    space_id: str,
    name: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    channel_id = await client.generate_id("Channel")
    return await create_node(
        node_id=channel_id,
        attributes={
            "type": "channel",
            "name": name,
            "parentId": space_id,
            "avatar": None,
        },
        client=client,
    )


async def list_channels(
    space_id: str,
    *,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    return await list_children(space_id, node_type="channel", client=client)


async def create_chat(
    collaborator_id: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "chat.create",
            "userId": session["userId"],
            "collaboratorId": collaborator_id,
        }
    )
    return mutation_ok(result)


async def list_messages(
    parent_id: str,
    *,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    return await list_children(parent_id, node_type="message", client=client)


async def send_message(
    parent_id: str,
    *,
    text: str | None = None,
    content: dict[str, Any] | None = None,
    reference_id: str | None = None,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    if content is None:
        if not text:
            raise KeyError("text or content is required")
        content = plain_text_to_tiptap(text)
    result = await client.mutation(
        {
            "type": "message.create",
            "userId": session["userId"],
            "parentId": parent_id,
            "content": content,
            "referenceId": reference_id,
        }
    )
    return mutation_ok(result)


async def delete_message(
    message_id: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    node = await get_node(message_id, client=client)
    if node is None or node.get("type") != "message":
        raise LookupError(f"Message not found: {message_id}")
    return await delete_node(message_id, client=client)
