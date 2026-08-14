from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from sci_colanode_api.accounts.crypto import resolve_bridge_secret

COOKIE_NAME = "sc_bridge_session"
SESSION_TTL_SECONDS = 60 * 60 * 12


def _sign(payload_b64: str) -> str:
    secret = resolve_bridge_secret().encode("utf-8")
    return hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()


def create_session_token(account_id: str, *, is_master: bool) -> str:
    payload = {
        "aid": account_id,
        "master": bool(is_master),
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
    }
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode(
        "ascii"
    )
    return f"{raw}.{_sign(raw)}"


def parse_session_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    raw, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(_sign(raw), sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(raw.encode("ascii")))
    except Exception:
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    if not payload.get("aid"):
        return None
    return payload
