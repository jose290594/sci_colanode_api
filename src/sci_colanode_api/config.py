from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Optional legacy single-account fallback (unused when store is bootstrapped)
    colanode_server_url: str = ""
    colanode_email: str = ""
    colanode_password: str = ""
    colanode_workspace_id: str | None = None

    colanode_data_dir: str = str(ROOT_DIR / "data")
    colanode_assets_dir: str = str(ROOT_DIR / "vendor" / "colanode" / "assets")

    sidecar_url: str = "http://127.0.0.1:3921"
    sidecar_host: str = "127.0.0.1"
    sidecar_port: int = 3921
    sidecar_auto_start: bool = True
    sidecar_dir: str = str(ROOT_DIR / "sidecar")

    bridge_secret: str = ""
    bridge_host: str = "127.0.0.1"
    bridge_port: int = 8786
    bridge_mode: str = "http"
    public_base_url: str = "http://127.0.0.1:8786"
    mcp_dns_rebinding_protection: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
