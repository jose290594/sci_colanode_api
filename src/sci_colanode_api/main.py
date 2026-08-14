from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.transport_security import TransportSecuritySettings

from sci_colanode_api.api.admin_routes import router as admin_router
from sci_colanode_api.api.middleware import AccountAuthMiddleware
from sci_colanode_api.api.routes import router
from sci_colanode_api.config import get_settings
from sci_colanode_api.mcp.tools import create_mcp
from sci_colanode_api.sidecar import ensure_sidecar, reset_sidecar, stop_sidecar
from sci_colanode_api import __version__

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    mcp = create_mcp()

    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=settings.mcp_dns_rebinding_protection,
    )
    mcp_asgi = mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        transport_security=transport_security,
        host=settings.bridge_host,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(mcp_asgi.router.lifespan_context(mcp_asgi))
            await ensure_sidecar(settings, restart=True)
            try:
                yield
            finally:
                await reset_sidecar()
                stop_sidecar()

    app = FastAPI(
        title="SCI Colanode Bridge",
        version=__version__,
        lifespan=lifespan,
    )
    # Pure ASGI middleware (preserves ContextVar into MCP tool tasks)
    app.add_middleware(AccountAuthMiddleware)
    app.include_router(router)
    app.include_router(admin_router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/mcp", mcp_asgi)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": "sci-colanode-api",
            "rest": "/v1",
            "mcp": "/mcp/",
            "admin": "/admin",
            "docs": "/docs",
        }

    @app.get("/admin")
    async def admin_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "admin.html")

    @app.get("/admin/")
    async def admin_page_slash() -> RedirectResponse:
        return RedirectResponse(url="/admin", status_code=307)

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "sci_colanode_api.main:app",
        host=settings.bridge_host,
        port=settings.bridge_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
