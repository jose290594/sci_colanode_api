from __future__ import annotations

from typing import Any

import httpx

from sci_colanode_api.accounts.context import get_current_account, require_current_account
from sci_colanode_api.accounts.store import AccountRecord
from sci_colanode_api.config import Settings, get_settings


class SidecarError(RuntimeError):
    def __init__(self, message: str, *, code: str = "sidecar_error", status: int = 500):
        super().__init__(message)
        self.code = code
        self.status = status


class SidecarClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        account: AccountRecord | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.account = account
        self._client = httpx.AsyncClient(
            base_url=self.settings.sidecar_url.rstrip("/"),
            timeout=httpx.Timeout(120.0, connect=30.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _require_account(self) -> AccountRecord:
        if self.account is not None:
            return self.account
        return require_current_account()

    async def health(self) -> dict[str, Any]:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

    async def ensure_auth(self, *, force_login: bool = False) -> dict[str, Any]:
        account = self._require_account()
        payload_body: dict[str, Any] = {
            "accountId": account.id,
            "forceLogin": force_login,
            "serverUrl": account.server_url,
            "email": account.email,
            "password": account.colanode_password(),
        }
        if account.workspace_id:
            payload_body["workspaceId"] = account.workspace_id

        response = await self._client.post("/auth/ensure", json=payload_body)
        payload = response.json()
        if not payload.get("ok"):
            error = payload.get("error") or {}
            raise SidecarError(
                error.get("message", "auth failed"),
                code=error.get("code", "auth_failed"),
                status=response.status_code,
            )
        return payload["session"]

    async def rpc(self, op: str, input: dict[str, Any] | None = None) -> Any:
        account = self._require_account()
        response = await self._client.post(
            "/rpc",
            json={"op": op, "input": input or {}, "accountId": account.id},
            headers={"X-Account-Id": account.id},
        )
        payload = response.json()
        if not payload.get("ok"):
            error = payload.get("error") or {}
            raise SidecarError(
                error.get("message", "rpc failed"),
                code=error.get("code", "rpc_error"),
                status=response.status_code,
            )
        return payload.get("result")

    async def mutation(self, input: dict[str, Any]) -> Any:
        return await self.rpc("mutation", input)

    async def query(self, input: dict[str, Any]) -> Any:
        return await self.rpc("query", input)

    async def generate_id(self, type_name: str = "Node") -> str:
        result = await self.rpc("generate_id", {"type": type_name})
        return str(result)

    async def generate_index(
        self,
        previous: str | None = None,
        next: str | None = None,
    ) -> str:
        result = await self.rpc(
            "generate_index",
            {"previous": previous, "next": next},
        )
        return str(result)

    async def session(self) -> dict[str, Any] | None:
        return await self.rpc("session.get")

    async def retry_pending_uploads(self) -> Any:
        return await self.rpc("file.retry_pending")

    async def set_document_content(
        self,
        *,
        user_id: str,
        document_id: str,
        content: str | dict[str, Any],
    ) -> Any:
        return await self.rpc(
            "document.set_content",
            {
                "userId": user_id,
                "documentId": document_id,
                "content": content,
            },
        )


_shared_http: SidecarClient | None = None


def get_sidecar(account: AccountRecord | None = None) -> SidecarClient:
    """Return a client bound to ``account`` or the current request account."""
    bound = account or get_current_account()
    if bound is None:
        raise SidecarError(
            "No Colanode account in request context (missing or invalid API key)",
            code="account_required",
            status=401,
        )
    return SidecarClient(account=bound)


async def reset_sidecar() -> None:
    global _shared_http
    if _shared_http is not None:
        await _shared_http.aclose()
        _shared_http = None
