from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

from sci_colanode_api.config import get_settings


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def resolve_bridge_secret() -> str:
    """Return BRIDGE_SECRET, or load/create data/.bridge_secret for local use."""
    settings = get_settings()
    if settings.bridge_secret.strip():
        return settings.bridge_secret.strip()

    data_dir = Path(settings.colanode_data_dir)
    if not data_dir.is_absolute():
        from sci_colanode_api.config import ROOT_DIR

        data_dir = ROOT_DIR / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / ".bridge_secret"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    secret = base64.urlsafe_b64encode(hashlib.sha256(Fernet.generate_key()).digest()).decode(
        "ascii"
    )
    path.write_text(secret + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return secret


def get_fernet() -> Fernet:
    return Fernet(_derive_fernet_key(resolve_bridge_secret()))


def encrypt_password(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_password(token: str) -> str:
    try:
        return get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("invalid_encrypted_password") from exc


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plaintext: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False
