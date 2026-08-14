from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Any

from sci_colanode_api.accounts.context import require_current_account
from sci_colanode_api.config import ROOT_DIR, get_settings
from sci_colanode_api.services import mutation_ok, require_session
from sci_colanode_api.services.nodes import get_node
from sci_colanode_api.sidecar.client import SidecarClient, get_sidecar

MCP_DOWNLOAD_MAX_BYTES = 5 * 1024 * 1024
DOWNLOAD_COMPLETED = 2
DOWNLOAD_FAILED = 3
FILE_STATUS_PENDING = 0
FILE_STATUS_READY = 1
FILE_STATUS_ERROR = 2


def extract_file_subtype(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("application/pdf"):
        return "pdf"
    return "other"


def _data_dir() -> Path:
    settings = get_settings()
    data_dir = Path(settings.colanode_data_dir)
    if not data_dir.is_absolute():
        data_dir = ROOT_DIR / data_dir
    return data_dir


def account_temp_dir() -> Path:
    account = require_current_account()
    path = _data_dir() / "accounts" / account.id / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def upload_file(
    parent_id: str,
    name: str,
    data: bytes,
    *,
    mime_type: str | None = None,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    session = await require_session(client)
    guessed, _ = mimetypes.guess_type(name)
    mime = mime_type or guessed or "application/octet-stream"
    ext = Path(name).suffix.lstrip(".") or "bin"
    subtype = extract_file_subtype(mime)

    temp_file_id = await client.generate_id("TempFile")
    dest = account_temp_dir() / f"{temp_file_id}.{ext}"
    dest.write_bytes(data)

    created = await client.mutation(
        {
            "type": "temp.file.create",
            "id": temp_file_id,
            "name": name,
            "size": len(data),
            "mimeType": mime,
            "subtype": subtype,
            "extension": ext,
            "path": str(dest.resolve()),
        }
    )
    mutation_ok(created)

    result = await client.mutation(
        {
            "type": "file.create",
            "userId": session["userId"],
            "parentId": parent_id,
            "tempFileId": temp_file_id,
        }
    )
    mutation_ok(result)
    file_id = None
    if isinstance(result, dict):
        file_id = (result.get("output") or {}).get("id") or result.get("id")
    if not file_id:
        return {"id": None, "name": name, "parentId": parent_id, "mimeType": mime}
    return await wait_until_file_ready(file_id, client=client)


async def wait_until_file_ready(
    file_id: str,
    *,
    timeout: float = 90.0,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    """Wait until the file node is synced and the TUS upload reaches Ready."""
    client = client or get_sidecar()
    deadline = asyncio.get_event_loop().time() + timeout
    node: dict[str, Any] | None = None
    while asyncio.get_event_loop().time() < deadline:
        node = await get_node(file_id, client=client)
        if node is None:
            await asyncio.sleep(0.5)
            continue
        status = node.get("status")
        if status == FILE_STATUS_ERROR:
            raise RuntimeError(f"File upload failed: {file_id}")
        if status == FILE_STATUS_READY and (node.get("serverRevision") or 0) > 0:
            return node
        await asyncio.sleep(0.8)
    raise TimeoutError(
        f"Timed out waiting for file {file_id} to become Ready; last={node}"
    )


async def wait_local_file(
    file_id: str,
    *,
    timeout: float = 60.0,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    client = client or get_sidecar()
    session = await require_session(client)
    deadline = asyncio.get_event_loop().time() + timeout
    local: dict[str, Any] | None = None
    auto = True
    while asyncio.get_event_loop().time() < deadline:
        local = await client.query(
            {
                "type": "local.file.get",
                "fileId": file_id,
                "userId": session["userId"],
                "autoDownload": auto,
            }
        )
        auto = False
        if isinstance(local, dict):
            status = local.get("downloadStatus")
            path = Path(str(local.get("path") or ""))
            if status == DOWNLOAD_FAILED:
                raise RuntimeError(
                    local.get("downloadErrorMessage") or "file_download_failed"
                )
            if path.is_file() and path.stat().st_size > 0 and status in {
                DOWNLOAD_COMPLETED,
                None,
            }:
                return local
            if status == DOWNLOAD_COMPLETED and path.is_file():
                return local
        await asyncio.sleep(0.4)
    raise TimeoutError(f"Timed out downloading file {file_id}; last={local}")


async def read_file_bytes(
    file_id: str,
    *,
    client: SidecarClient | None = None,
) -> tuple[bytes, dict[str, Any]]:
    client = client or get_sidecar()
    node = await get_node(file_id, client=client)
    if node is None or node.get("type") != "file":
        raise LookupError(f"File not found: {file_id}")
    local = await wait_local_file(file_id, client=client)
    path = Path(str(local.get("path") or ""))
    if not path.is_file():
        raise RuntimeError("downloaded file path is missing")
    return path.read_bytes(), {**node, "local": local}


async def download_file_payload(
    file_id: str,
    *,
    max_bytes: int = MCP_DOWNLOAD_MAX_BYTES,
    client: SidecarClient | None = None,
) -> dict[str, Any]:
    import base64

    data, meta = await read_file_bytes(file_id, client=client)
    if len(data) > max_bytes:
        raise ValueError(
            f"File is {len(data)} bytes; MCP download is limited to {max_bytes}. Use REST GET /v1/files/{{id}}/download."
        )
    name = meta.get("name") or meta.get("originalName") or file_id
    mime = meta.get("mimeType") or "application/octet-stream"
    return {
        "id": file_id,
        "name": name,
        "mimeType": mime,
        "size": len(data),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }
