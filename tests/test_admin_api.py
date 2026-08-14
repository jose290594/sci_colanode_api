from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sci_colanode_api.accounts.store import reset_store_singleton
from sci_colanode_api.api.admin_routes import router
from sci_colanode_api.config import get_settings


def test_admin_bootstrap_login_keys(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BRIDGE_SECRET", "unit-test-secret-value-32chars!!")
    monkeypatch.setenv("COLANODE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bridge.example.com")
    get_settings.cache_clear()
    reset_store_singleton()

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    st = client.get("/api/admin/status")
    assert st.status_code == 200
    assert st.json()["bootstrapped"] is False

    boot = client.post(
        "/api/admin/bootstrap",
        json={
            "label": "Master",
            "server_url": "https://colanode.example/config",
            "email": "master@example.com",
            "password": "secret123",
        },
    )
    assert boot.status_code == 200, boot.text
    body = boot.json()
    assert body["account"]["is_master"] is True
    assert body["api_key"].startswith("sc_mcp_")
    assert "sci-colanode" in body["mcp_snippet"]["mcpServers"]
    assert body["mcp_snippet"]["mcpServers"]["sci-colanode"]["url"].endswith("/mcp/")

    denied = client.post(
        "/api/admin/bootstrap",
        json={
            "server_url": "https://x",
            "email": "x@y.z",
            "password": "pw",
        },
    )
    assert denied.status_code == 400

    client.post("/api/admin/logout")
    bad = client.post(
        "/api/admin/login",
        json={"email": "master@example.com", "password": "wrong"},
    )
    assert bad.status_code == 401

    ok = client.post(
        "/api/admin/login",
        json={"email": "master@example.com", "password": "secret123"},
    )
    assert ok.status_code == 200
    accounts = client.get("/api/admin/accounts")
    assert accounts.status_code == 200
    assert len(accounts.json()["accounts"]) == 1
