from __future__ import annotations

import json
import secrets
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sci_colanode_api.accounts import api_keys as keys_mod
from sci_colanode_api.accounts.crypto import (
    decrypt_password,
    encrypt_password,
    hash_password,
    verify_password,
)
from sci_colanode_api.config import ROOT_DIR, get_settings


@dataclass
class AccountRecord:
    id: str
    label: str
    server_url: str
    email: str
    password_hash: str
    password_enc: str
    workspace_id: str | None = None
    is_master: bool = False
    created_at: str = ""
    updated_at: str = ""
    api_keys: list[dict[str, Any]] = field(default_factory=list)

    def public_dict(self, *, include_email: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "server_url": self.server_url,
            "workspace_id": self.workspace_id or "",
            "is_master": self.is_master,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "api_keys": [keys_mod.public_key_row(k) for k in self.api_keys],
        }
        if include_email:
            out["email"] = self.email
        return out

    def colanode_password(self) -> str:
        return decrypt_password(self.password_enc)


@dataclass
class StoreData:
    version: int = 1
    accounts: list[AccountRecord] = field(default_factory=list)


class AccountStore:
    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        data_dir = Path(settings.colanode_data_dir)
        if not data_dir.is_absolute():
            data_dir = ROOT_DIR / data_dir
        self.path = path or (data_dir / "store.json")
        self._lock = threading.RLock()

    def _empty(self) -> StoreData:
        return StoreData()

    def _load(self) -> StoreData:
        if not self.path.is_file():
            return self._empty()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        accounts: list[AccountRecord] = []
        for row in raw.get("accounts") or []:
            accounts.append(
                AccountRecord(
                    id=str(row["id"]),
                    label=str(row.get("label") or ""),
                    server_url=str(row.get("server_url") or ""),
                    email=str(row.get("email") or ""),
                    password_hash=str(row.get("password_hash") or ""),
                    password_enc=str(row.get("password_enc") or ""),
                    workspace_id=(str(row["workspace_id"]) if row.get("workspace_id") else None),
                    is_master=bool(row.get("is_master")),
                    created_at=str(row.get("created_at") or ""),
                    updated_at=str(row.get("updated_at") or ""),
                    api_keys=list(row.get("api_keys") or []),
                )
            )
        return StoreData(version=int(raw.get("version") or 1), accounts=accounts)

    def _save(self, data: StoreData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": data.version,
            "accounts": [asdict(a) for a in data.accounts],
        }
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def bootstrapped(self) -> bool:
        with self._lock:
            return len(self._load().accounts) > 0

    def list_accounts(self) -> list[AccountRecord]:
        with self._lock:
            return list(self._load().accounts)

    def get_account(self, account_id: str) -> AccountRecord | None:
        with self._lock:
            for acc in self._load().accounts:
                if acc.id == account_id:
                    return acc
            return None

    def find_by_email(self, email: str) -> AccountRecord | None:
        needle = email.strip().lower()
        with self._lock:
            for acc in self._load().accounts:
                if acc.email.strip().lower() == needle:
                    return acc
            return None

    def create_account(
        self,
        *,
        label: str,
        server_url: str,
        email: str,
        password: str,
        workspace_id: str | None = None,
        is_master: bool = False,
    ) -> AccountRecord:
        with self._lock:
            data = self._load()
            if any(a.email.strip().lower() == email.strip().lower() for a in data.accounts):
                raise ValueError("email_already_exists")
            if is_master and any(a.is_master for a in data.accounts):
                raise ValueError("master_already_exists")
            now = keys_mod.utcnow()
            account = AccountRecord(
                id="acc_" + secrets.token_urlsafe(12),
                label=label.strip() or email.strip(),
                server_url=server_url.strip().rstrip("/"),
                email=email.strip(),
                password_hash=hash_password(password),
                password_enc=encrypt_password(password),
                workspace_id=(workspace_id.strip() if workspace_id else None) or None,
                is_master=is_master,
                created_at=now,
                updated_at=now,
            )
            data.accounts.append(account)
            self._save(data)
            return account

    def update_account(
        self,
        account_id: str,
        *,
        label: str | None = None,
        server_url: str | None = None,
        email: str | None = None,
        password: str | None = None,
        workspace_id: str | None = None,
        clear_workspace: bool = False,
    ) -> AccountRecord:
        with self._lock:
            data = self._load()
            acc = next((a for a in data.accounts if a.id == account_id), None)
            if acc is None:
                raise KeyError("account_not_found")
            if email is not None:
                other = next(
                    (
                        a
                        for a in data.accounts
                        if a.id != account_id and a.email.strip().lower() == email.strip().lower()
                    ),
                    None,
                )
                if other:
                    raise ValueError("email_already_exists")
                acc.email = email.strip()
            if label is not None:
                acc.label = label.strip() or acc.email
            if server_url is not None:
                acc.server_url = server_url.strip().rstrip("/")
            if password is not None and password != "":
                acc.password_hash = hash_password(password)
                acc.password_enc = encrypt_password(password)
            if clear_workspace:
                acc.workspace_id = None
            elif workspace_id is not None:
                acc.workspace_id = workspace_id.strip() or None
            acc.updated_at = keys_mod.utcnow()
            self._save(data)
            return acc

    def delete_account(self, account_id: str) -> None:
        with self._lock:
            data = self._load()
            acc = next((a for a in data.accounts if a.id == account_id), None)
            if acc is None:
                raise KeyError("account_not_found")
            if acc.is_master:
                raise ValueError("cannot_delete_master")
            data.accounts = [a for a in data.accounts if a.id != account_id]
            self._save(data)

    def verify_login(self, email: str, password: str) -> AccountRecord | None:
        acc = self.find_by_email(email)
        if acc is None:
            return None
        if not verify_password(password, acc.password_hash):
            return None
        return acc

    def create_api_key(self, account_id: str, name: str = "") -> tuple[AccountRecord, str]:
        with self._lock:
            data = self._load()
            acc = next((a for a in data.accounts if a.id == account_id), None)
            if acc is None:
                raise KeyError("account_not_found")
            if len(acc.api_keys) >= keys_mod.MAX_KEYS_PER_ACCOUNT:
                raise ValueError("api_key_limit")
            plaintext = keys_mod.make_api_key_plaintext()
            entry = {
                "id": "key_" + secrets.token_urlsafe(8),
                "name": (name or "default").strip(),
                "hash": keys_mod.hash_api_key(plaintext),
                "prefix": keys_mod.display_prefix(plaintext),
                "created_at": keys_mod.utcnow(),
                "last_used_at": None,
            }
            acc.api_keys.append(entry)
            acc.updated_at = keys_mod.utcnow()
            self._save(data)
            return acc, plaintext

    def revoke_api_key(self, account_id: str, key_id: str) -> AccountRecord:
        with self._lock:
            data = self._load()
            acc = next((a for a in data.accounts if a.id == account_id), None)
            if acc is None:
                raise KeyError("account_not_found")
            before = len(acc.api_keys)
            acc.api_keys = [k for k in acc.api_keys if str(k.get("id")) != key_id]
            if len(acc.api_keys) == before:
                raise KeyError("api_key_not_found")
            acc.updated_at = keys_mod.utcnow()
            self._save(data)
            return acc

    def resolve_api_key(self, plaintext: str) -> AccountRecord | None:
        if not keys_mod.is_api_key_token(plaintext):
            return None
        digest = keys_mod.hash_api_key(plaintext)
        with self._lock:
            data = self._load()
            for acc in data.accounts:
                for key in acc.api_keys:
                    if str(key.get("hash")) == digest:
                        key["last_used_at"] = keys_mod.utcnow()
                        self._save(data)
                        return acc
            return None


_store: AccountStore | None = None


def get_store() -> AccountStore:
    global _store
    if _store is None:
        _store = AccountStore()
    return _store


def reset_store_singleton() -> None:
    global _store
    _store = None
