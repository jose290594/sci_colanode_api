from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

API_KEY_PREFIX = "sc_mcp_"
MAX_KEYS_PER_ACCOUNT = 10
_SECRET_BYTES = 24
_PREFIX_DISPLAY_LEN = 12


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def make_api_key_plaintext() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(_SECRET_BYTES)}"


def display_prefix(plaintext: str) -> str:
    return plaintext[:_PREFIX_DISPLAY_LEN]


def is_api_key_token(token: str) -> bool:
    return token.startswith(API_KEY_PREFIX) and len(token) > len(API_KEY_PREFIX) + 8


def public_key_row(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(entry.get("id") or ""),
        "name": str(entry.get("name") or ""),
        "prefix": str(entry.get("prefix") or ""),
        "created_at": entry.get("created_at"),
        "last_used_at": entry.get("last_used_at"),
    }
