from __future__ import annotations

from pathlib import Path

from sci_colanode_api.accounts.api_keys import hash_api_key, is_api_key_token, make_api_key_plaintext
from sci_colanode_api.accounts.crypto import (
    decrypt_password,
    encrypt_password,
    hash_password,
    verify_password,
)
from sci_colanode_api.accounts.store import AccountStore
from sci_colanode_api.config import get_settings


def test_password_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BRIDGE_SECRET", "unit-test-secret-value-32chars!!")
    get_settings.cache_clear()
    monkeypatch.setenv("COLANODE_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    enc = encrypt_password("s3cret")
    assert decrypt_password(enc) == "s3cret"
    h = hash_password("s3cret")
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)


def test_store_bootstrap_and_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BRIDGE_SECRET", "unit-test-secret-value-32chars!!")
    monkeypatch.setenv("COLANODE_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    store = AccountStore(path=tmp_path / "store.json")
    assert not store.bootstrapped()
    master = store.create_account(
        label="Master",
        server_url="https://example.com/config",
        email="master@example.com",
        password="pass1234",
        is_master=True,
    )
    assert master.is_master
    assert store.bootstrapped()
    assert store.verify_login("master@example.com", "pass1234")
    assert store.verify_login("master@example.com", "bad") is None

    _, plaintext = store.create_api_key(master.id, "cursor")
    assert is_api_key_token(plaintext)
    resolved = store.resolve_api_key(plaintext)
    assert resolved is not None
    assert resolved.id == master.id
    assert store.resolve_api_key(make_api_key_plaintext()) is None
    assert hash_api_key(plaintext) == store.get_account(master.id).api_keys[0]["hash"]
