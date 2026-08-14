from __future__ import annotations

from typing import Any

from sci_colanode_api.services import require_session
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


async def list_workspaces(client: SidecarClient | None = None) -> list[dict[str, Any]]:
    client = client or get_sidecar()
    await require_session(client)
    result = await client.query({"type": "workspace.list"})
    return list(result or [])
