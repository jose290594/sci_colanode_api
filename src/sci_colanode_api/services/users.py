from __future__ import annotations

from typing import Any

from sci_colanode_api.services import mutation_ok, require_session
from sci_colanode_api.services.nodes import get_node
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


async def list_collaborators(
    node_id: str,
    *,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    node = await get_node(node_id, client=client)
    if node is None:
        raise LookupError(f"Node not found: {node_id}")
    return {
        "node_id": node_id,
        "collaborators": node.get("collaborators") or {},
    }


async def add_collaborators(
    node_id: str,
    collaborator_ids: list[str],
    role: str = "editor",
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "node.collaborator.create",
            "userId": session["userId"],
            "nodeId": node_id,
            "collaboratorIds": collaborator_ids,
            "role": role,
        }
    )
    return mutation_ok(result)


async def update_collaborator(
    node_id: str,
    collaborator_id: str,
    role: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "node.collaborator.update",
            "userId": session["userId"],
            "nodeId": node_id,
            "collaboratorId": collaborator_id,
            "role": role,
        }
    )
    return mutation_ok(result)


async def remove_collaborator(
    node_id: str,
    collaborator_id: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "node.collaborator.delete",
            "userId": session["userId"],
            "nodeId": node_id,
            "collaboratorId": collaborator_id,
        }
    )
    return mutation_ok(result)


async def list_users(*, client: SidecarClient | None = None) -> list[dict[str, Any]]:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.query({"type": "user.list", "userId": session["userId"]})
    return list(result or [])


async def search_users(
    query: str,
    *,
    exclude: list[str] | None = None,
    client: SidecarClient | None = None,
) -> list[dict[str, Any]]:
    client = client or get_sidecar()
    session = await require_session(client)
    payload: dict[str, Any] = {
        "type": "user.search",
        "searchQuery": query,
        "userId": session["userId"],
    }
    if exclude:
        payload["exclude"] = exclude
    result = await client.query(payload)
    return list(result or [])


async def invite_users(
    users: list[dict[str, str]],
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    session = await require_session(client)
    result = await client.mutation(
        {
            "type": "users.create",
            "userId": session["userId"],
            "users": users,
        }
    )
    return mutation_ok(result)


async def update_user_role(
    user_id: str,
    role: str,
    *,
    client: SidecarClient | None = None,
) -> Any:
    client = client or get_sidecar()
    await require_session(client)
    result = await client.mutation(
        {
            "type": "user.role.update",
            "userId": user_id,
            "role": role,
        }
    )
    return mutation_ok(result)
