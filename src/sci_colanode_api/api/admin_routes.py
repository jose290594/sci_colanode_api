from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from sci_colanode_api.accounts.admin_session import (
    COOKIE_NAME,
    create_session_token,
    parse_session_token,
)
from sci_colanode_api.accounts.store import AccountRecord, get_store
from sci_colanode_api.config import get_settings

router = APIRouter(prefix="/api/admin")


class BootstrapBody(BaseModel):
    label: str = ""
    server_url: str
    email: str
    password: str
    workspace_id: str | None = None


class LoginBody(BaseModel):
    email: str
    password: str


class AccountUpdateBody(BaseModel):
    label: str | None = None
    server_url: str | None = None
    email: str | None = None
    password: str | None = None
    workspace_id: str | None = None
    clear_workspace: bool = False


class AccountCreateBody(BaseModel):
    label: str = ""
    server_url: str
    email: str
    password: str
    workspace_id: str | None = None


class ApiKeyCreateBody(BaseModel):
    name: str = "default"


def _session_account(request: Request) -> AccountRecord:
    token = request.cookies.get(COOKIE_NAME)
    payload = parse_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="not_authenticated")
    account = get_store().get_account(str(payload["aid"]))
    if account is None:
        raise HTTPException(status_code=401, detail="session_account_missing")
    return account


def _set_session_cookie(
    response: Response, account: AccountRecord, *, request: Request
) -> None:
    secure = request.url.scheme == "https"
    response.set_cookie(
        COOKIE_NAME,
        create_session_token(account.id, is_master=account.is_master),
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 12,
        path="/",
    )


@router.get("/status")
async def admin_status(request: Request) -> dict[str, Any]:
    store = get_store()
    bootstrapped = store.bootstrapped()
    me = None
    token = request.cookies.get(COOKIE_NAME)
    payload = parse_session_token(token)
    if payload:
        acc = store.get_account(str(payload["aid"]))
        if acc:
            me = acc.public_dict()
    return {
        "bootstrapped": bootstrapped,
        "me": me,
        "public_base_url": get_settings().public_base_url.rstrip("/"),
    }


@router.post("/bootstrap")
async def admin_bootstrap(body: BootstrapBody, request: Request, response: Response) -> dict[str, Any]:
    store = get_store()
    if store.bootstrapped():
        raise HTTPException(status_code=400, detail="already_bootstrapped")
    if not body.server_url.strip() or not body.email.strip() or not body.password:
        raise HTTPException(status_code=400, detail="missing_fields")
    account = store.create_account(
        label=body.label or body.email,
        server_url=body.server_url,
        email=body.email,
        password=body.password,
        workspace_id=body.workspace_id,
        is_master=True,
    )
    account, api_key = store.create_api_key(account.id, "default")
    _set_session_cookie(response, account, request=request)
    return {
        "account": account.public_dict(),
        "api_key": api_key,
        "mcp_snippet": _mcp_snippet(api_key),
    }


@router.post("/login")
async def admin_login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
    account = get_store().verify_login(body.email, body.password)
    if account is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    _set_session_cookie(response, account, request=request)
    return {"account": account.public_dict()}


@router.post("/logout")
async def admin_logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/accounts")
async def list_accounts(request: Request) -> dict[str, Any]:
    me = _session_account(request)
    store = get_store()
    if me.is_master:
        rows = [a.public_dict() for a in store.list_accounts()]
    else:
        rows = [me.public_dict()]
    return {"accounts": rows, "me": me.public_dict()}


@router.post("/accounts")
async def create_account(request: Request, body: AccountCreateBody) -> dict[str, Any]:
    me = _session_account(request)
    if not me.is_master:
        raise HTTPException(status_code=403, detail="master_required")
    try:
        account = get_store().create_account(
            label=body.label or body.email,
            server_url=body.server_url,
            email=body.email,
            password=body.password,
            workspace_id=body.workspace_id,
            is_master=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account.public_dict()}


@router.put("/accounts/{account_id}")
async def update_account(
    request: Request, account_id: str, body: AccountUpdateBody
) -> dict[str, Any]:
    me = _session_account(request)
    if not me.is_master and me.id != account_id:
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        account = get_store().update_account(
            account_id,
            label=body.label,
            server_url=body.server_url,
            email=body.email,
            password=body.password,
            workspace_id=body.workspace_id,
            clear_workspace=body.clear_workspace,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account.public_dict()}


@router.delete("/accounts/{account_id}")
async def delete_account(request: Request, account_id: str) -> dict[str, bool]:
    me = _session_account(request)
    if not me.is_master:
        raise HTTPException(status_code=403, detail="master_required")
    try:
        get_store().delete_account(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/accounts/{account_id}/api-keys")
async def create_api_key(
    request: Request, account_id: str, body: ApiKeyCreateBody
) -> dict[str, Any]:
    me = _session_account(request)
    if not me.is_master and me.id != account_id:
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        account, plaintext = get_store().create_api_key(account_id, body.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "account": account.public_dict(),
        "api_key": plaintext,
        "mcp_snippet": _mcp_snippet(plaintext),
    }


@router.delete("/accounts/{account_id}/api-keys/{key_id}")
async def revoke_api_key(request: Request, account_id: str, key_id: str) -> dict[str, Any]:
    me = _session_account(request)
    if not me.is_master and me.id != account_id:
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        account = get_store().revoke_api_key(account_id, key_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"account": account.public_dict()}


@router.get("/accounts/{account_id}/mcp-snippet")
async def mcp_snippet(request: Request, account_id: str) -> dict[str, Any]:
    me = _session_account(request)
    if not me.is_master and me.id != account_id:
        raise HTTPException(status_code=403, detail="forbidden")
    account = get_store().get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    return {
        "account_id": account_id,
        "hint": "Generate or rotate an API key to get a ready-to-paste mcp.json with the secret.",
        "template": _mcp_snippet("<sc_mcp_YOUR_KEY>"),
        "keys": account.public_dict()["api_keys"],
    }


def _mcp_snippet(api_key: str) -> dict[str, Any]:
    base = get_settings().public_base_url.rstrip("/")
    url = base + "/mcp/"
    return {
        "mcpServers": {
            "sci-colanode": {
                "url": url,
                "headers": {"Authorization": f"Bearer {api_key}"},
            }
        }
    }
