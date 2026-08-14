"""Smoke: ensure store has an account, then list workspaces via sidecar."""

from __future__ import annotations

import asyncio
import os
import sys

from sci_colanode_api.accounts.context import set_current_account
from sci_colanode_api.accounts.store import get_store
from sci_colanode_api.sidecar import ensure_sidecar, get_sidecar, stop_sidecar


async def main() -> None:
    store = get_store()
    account_id = (os.environ.get("SC_ACCOUNT_ID") or "").strip()
    if account_id:
        account = store.get_account(account_id)
    else:
        accounts = store.list_accounts()
        account = next((a for a in accounts if a.is_master), accounts[0] if accounts else None)
    if account is None:
        print("No accounts in data/store.json — open /admin first", file=sys.stderr)
        raise SystemExit(1)

    set_current_account(account)
    await ensure_sidecar()
    session = await get_sidecar().ensure_auth()
    print("auth_ok", session)
    workspaces = await get_sidecar().query({"type": "workspace.list"})
    print("workspaces", workspaces)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        stop_sidecar()
