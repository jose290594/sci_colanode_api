from __future__ import annotations

from contextvars import ContextVar

from sci_colanode_api.accounts.store import AccountRecord

_current_account: ContextVar[AccountRecord | None] = ContextVar(
    "colanode_bridge_account", default=None
)


def set_current_account(account: AccountRecord | None):
    return _current_account.set(account)


def reset_current_account(token) -> None:
    _current_account.reset(token)


def get_current_account() -> AccountRecord | None:
    return _current_account.get()


def require_current_account() -> AccountRecord:
    account = get_current_account()
    if account is None:
        raise PermissionError("account_context_missing")
    return account
