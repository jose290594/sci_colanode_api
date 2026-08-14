from __future__ import annotations

from typing import Any

from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar


async def require_session(client: SidecarClient | None = None) -> dict[str, Any]:
    client = client or get_sidecar()
    session = await client.session()
    if session:
        return session
    return await client.ensure_auth()


def mutation_ok(result: Any) -> Any:
    if isinstance(result, dict) and result.get("success") is False:
        error = result.get("error") or {}
        raise RuntimeError(
            f"{error.get('code', 'mutation_failed')}: {error.get('message', result)}"
        )
    return result
