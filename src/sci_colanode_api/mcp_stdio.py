from __future__ import annotations

import asyncio
import os

from sci_colanode_api.accounts.context import set_current_account
from sci_colanode_api.accounts.store import get_store
from sci_colanode_api.mcp.tools import create_mcp
from sci_colanode_api.sidecar import ensure_sidecar, get_sidecar, stop_sidecar


async def _run() -> None:
    store = get_store()
    account_id = (os.environ.get("SC_ACCOUNT_ID") or "").strip()
    if account_id:
        account = store.get_account(account_id)
    else:
        accounts = store.list_accounts()
        account = next((a for a in accounts if a.is_master), accounts[0] if accounts else None)
    if account is None:
        raise SystemExit(
            "No Colanode accounts configured. Open /admin to bootstrap, "
            "or set SC_ACCOUNT_ID to an existing account id."
        )
    set_current_account(account)
    await ensure_sidecar()
    await get_sidecar().ensure_auth()
    mcp = create_mcp()
    await mcp.run_stdio_async()


def main() -> None:
    try:
        asyncio.run(_run())
    finally:
        stop_sidecar()


if __name__ == "__main__":
    main()
