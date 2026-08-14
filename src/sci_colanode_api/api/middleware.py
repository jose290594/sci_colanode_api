from __future__ import annotations

from sci_colanode_api.accounts.context import reset_current_account, set_current_account
from sci_colanode_api.accounts.store import get_store


class AccountAuthMiddleware:
    """ASGI middleware: Bearer sc_mcp_… → account ContextVar for /v1 and /mcp."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        needs_api_key = path.startswith("/v1") or path.startswith("/mcp")
        token_ctx = None

        if needs_api_key:
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in (scope.get("headers") or [])
            }
            auth = headers.get("authorization") or ""
            if not auth.startswith("Bearer "):
                await self._json(send, 401, {"detail": "Missing Bearer token"})
                return
            raw = auth.removeprefix("Bearer ").strip()
            account = get_store().resolve_api_key(raw)
            if account is None:
                await self._json(send, 403, {"detail": "Invalid API key"})
                return
            token_ctx = set_current_account(account)
            scope.setdefault("state", {})
            # Starlette request.state is set by ServerErrorMiddleware; stash on scope
            if "state" not in scope or not hasattr(scope["state"], "account"):
                pass

        try:
            await self.app(scope, receive, send)
        finally:
            if token_ctx is not None:
                reset_current_account(token_ctx)

    async def _json(self, send, status: int, body: dict) -> None:
        import json

        payload = json.dumps(body).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})
