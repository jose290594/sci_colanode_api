from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any

from sci_colanode_api.accounts.context import require_current_account
from sci_colanode_api.services import (
    chat,
    databases,
    files,
    folders,
    nodes,
    pages,
    records,
    spaces,
    users,
    workspaces,
)
from sci_colanode_api.sidecar import SidecarError, get_sidecar

router = APIRouter(prefix="/v1")


class CreateSpaceBody(BaseModel):
    name: str
    description: str | None = None
    visibility: str = "private"


class CreateFolderBody(BaseModel):
    name: str


class CreateRecordBody(BaseModel):
    name: str
    fields: dict[str, Any] | None = None


class UpdateRecordBody(BaseModel):
    name: str | None = None
    fields: dict[str, Any] | None = None


class CreatePageBody(BaseModel):
    name: str


class UpdatePageBody(BaseModel):
    name: str | None = None
    content: str | dict[str, Any] | None = None


class UpdateSpaceBody(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None


class RenameNodeBody(BaseModel):
    name: str


class ReorderSpaceBody(BaseModel):
    child_id: str
    after: str | None = None


class CreateDatabaseBody(BaseModel):
    space_id: str
    name: str


class CreateFieldBody(BaseModel):
    name: str
    type: str
    relation_database_id: str | None = None
    options: list[dict[str, Any]] | None = None


class UpdateFieldBody(BaseModel):
    name: str | None = None
    options: dict[str, Any] | None = None
    relation_database_id: str | None = None


class CreateViewBody(BaseModel):
    name: str
    layout: str = "table"


class CreateChannelBody(BaseModel):
    name: str


class CreateChatBody(BaseModel):
    collaborator_id: str


class SendMessageBody(BaseModel):
    text: str | None = None
    content: dict[str, Any] | None = None
    reference_id: str | None = None


class CollaboratorsCreateBody(BaseModel):
    collaborator_ids: list[str]
    role: str = "editor"


class CollaboratorUpdateBody(BaseModel):
    role: str


class InviteUsersBody(BaseModel):
    users: list[dict[str, str]]


class UpdateUserRoleBody(BaseModel):
    role: str


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SidecarError):
        return HTTPException(status_code=exc.status, detail={"code": exc.code, "message": str(exc)})
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, TimeoutError):
        return HTTPException(status_code=504, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


async def _auth() -> None:
    require_current_account()
    await get_sidecar().ensure_auth()


@router.get("/health")
async def health() -> dict[str, Any]:
    try:
        account = require_current_account()
        payload = await get_sidecar().health()
    except Exception as exc:
        raise _http_error(exc) from exc
    return {"ok": True, "account_id": account.id, "sidecar": payload}


@router.get("/workspaces")
async def api_list_workspaces() -> list[dict[str, Any]]:
    try:
        await _auth()
        return await workspaces.list_workspaces()
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/spaces")
async def api_list_spaces() -> list[dict[str, Any]]:
    try:
        await _auth()
        return await spaces.list_spaces()
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/spaces")
async def api_create_space(body: CreateSpaceBody) -> dict[str, Any]:
    try:
        await _auth()
        return await spaces.create_space(
            body.name,
            description=body.description,
            visibility=body.visibility,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/nodes/{node_id}")
async def api_get_node(node_id: str) -> dict[str, Any]:
    try:
        await _auth()
        node = await nodes.get_node(node_id)
        if node is None:
            raise LookupError(f"Node not found: {node_id}")
        return node
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/nodes/{node_id}/children")
async def api_list_children(node_id: str, type: str | None = None) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await nodes.list_children(node_id, node_type=type)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/nodes/{node_id}/tree")
async def api_get_tree(node_id: str, depth: int = 3) -> dict[str, Any]:
    try:
        await _auth()
        return await nodes.get_tree(node_id, depth=depth)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.delete("/nodes/{node_id}")
async def api_delete_node(node_id: str) -> dict[str, Any]:
    try:
        await _auth()
        result = await nodes.delete_node(node_id)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/nodes/{parent_id}/folders")
async def api_create_folder(parent_id: str, body: CreateFolderBody) -> dict[str, Any]:
    try:
        await _auth()
        return await folders.create_folder(parent_id, body.name)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/databases")
async def api_list_databases(space_id: str | None = None) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await databases.list_databases(space_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/databases/{database_id}/schema")
async def api_database_schema(database_id: str) -> dict[str, Any]:
    try:
        await _auth()
        return await databases.get_database_schema(database_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/databases/{database_id}/records")
async def api_list_records(database_id: str) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await records.list_records(database_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/databases/{database_id}/records")
async def api_create_record(database_id: str, body: CreateRecordBody) -> dict[str, Any]:
    try:
        await _auth()
        return await records.create_record(database_id, body.name, body.fields)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/records/{record_id}")
async def api_get_record(record_id: str) -> dict[str, Any]:
    try:
        await _auth()
        return await records.get_record(record_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/records/{record_id}")
async def api_update_record(record_id: str, body: UpdateRecordBody) -> dict[str, Any]:
    try:
        await _auth()
        return await records.update_record(record_id, name=body.name, fields=body.fields)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/nodes/{parent_id}/pages")
async def api_create_page(parent_id: str, body: CreatePageBody) -> dict[str, Any]:
    try:
        await _auth()
        return await pages.create_page(parent_id, body.name)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/pages/{page_id}")
async def api_get_page(page_id: str) -> dict[str, Any]:
    try:
        await _auth()
        return await pages.get_page(page_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/pages/{page_id}")
async def api_update_page(page_id: str, body: UpdatePageBody) -> dict[str, Any]:
    try:
        await _auth()
        if body.name is not None:
            await pages.rename_page(page_id, body.name)
        if body.content is not None:
            await pages.update_page_content(page_id, body.content)
        return await pages.get_page(page_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/spaces/{space_id}")
async def api_update_space(space_id: str, body: UpdateSpaceBody) -> dict[str, Any]:
    try:
        await _auth()
        return await spaces.update_space(
            space_id,
            name=body.name,
            description=body.description,
            visibility=body.visibility,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/spaces/{space_id}/reorder")
async def api_reorder_space(space_id: str, body: ReorderSpaceBody) -> dict[str, Any]:
    try:
        await _auth()
        result = await spaces.reorder_space_child(space_id, body.child_id, after=body.after)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/nodes/{node_id}")
async def api_rename_node(node_id: str, body: RenameNodeBody) -> dict[str, Any]:
    try:
        await _auth()
        return await nodes.rename_node(node_id, body.name)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/nodes/{parent_id}/files")
async def api_upload_file(parent_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        await _auth()
        data = await file.read()
        return await files.upload_file(
            parent_id,
            file.filename or "upload.bin",
            data,
            mime_type=file.content_type,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/files/{file_id}/download")
async def api_download_file(file_id: str) -> Response:
    try:
        await _auth()
        data, meta = await files.read_file_bytes(file_id)
        name = meta.get("name") or meta.get("originalName") or file_id
        mime = meta.get("mimeType") or "application/octet-stream"
        return Response(
            content=data,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/databases")
async def api_create_database(body: CreateDatabaseBody) -> dict[str, Any]:
    try:
        await _auth()
        return await databases.create_database(body.space_id, body.name)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/databases/{database_id}/fields")
async def api_add_field(database_id: str, body: CreateFieldBody) -> dict[str, Any]:
    try:
        await _auth()
        return await databases.add_field(
            database_id,
            body.name,
            body.type,
            relation_database_id=body.relation_database_id,
            options=body.options,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/databases/{database_id}/fields/{field_id}")
async def api_update_field(database_id: str, field_id: str, body: UpdateFieldBody) -> dict[str, Any]:
    try:
        await _auth()
        return await databases.update_field(
            database_id,
            field_id,
            name=body.name,
            options=body.options,
            relation_database_id=body.relation_database_id,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.delete("/databases/{database_id}/fields/{field_id}")
async def api_delete_field(database_id: str, field_id: str) -> dict[str, Any]:
    try:
        await _auth()
        return await databases.delete_field(database_id, field_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/databases/{database_id}/views")
async def api_list_views(database_id: str) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await databases.list_views(database_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/databases/{database_id}/views")
async def api_create_view(database_id: str, body: CreateViewBody) -> dict[str, Any]:
    try:
        await _auth()
        return await databases.create_view(database_id, body.name, layout=body.layout)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/databases/{database_id}/records/search")
async def api_search_records(database_id: str, q: str = Query("")) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await records.search_records(database_id, q)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.delete("/records/{record_id}")
async def api_delete_record(record_id: str) -> dict[str, Any]:
    try:
        await _auth()
        result = await records.delete_record(record_id)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/spaces/{space_id}/channels")
async def api_create_channel(space_id: str, body: CreateChannelBody) -> dict[str, Any]:
    try:
        await _auth()
        return await chat.create_channel(space_id, body.name)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/spaces/{space_id}/channels")
async def api_list_channels(space_id: str) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await chat.list_channels(space_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/chats")
async def api_create_chat(body: CreateChatBody) -> dict[str, Any]:
    try:
        await _auth()
        return await chat.create_chat(body.collaborator_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/nodes/{parent_id}/messages")
async def api_list_messages(parent_id: str) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await chat.list_messages(parent_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/nodes/{parent_id}/messages")
async def api_send_message(parent_id: str, body: SendMessageBody) -> dict[str, Any]:
    try:
        await _auth()
        return await chat.send_message(
            parent_id,
            text=body.text,
            content=body.content,
            reference_id=body.reference_id,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/nodes/{node_id}/collaborators")
async def api_list_collaborators(node_id: str) -> dict[str, Any]:
    try:
        await _auth()
        return await users.list_collaborators(node_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/nodes/{node_id}/collaborators")
async def api_add_collaborators(node_id: str, body: CollaboratorsCreateBody) -> dict[str, Any]:
    try:
        await _auth()
        result = await users.add_collaborators(
            node_id, body.collaborator_ids, role=body.role
        )
        return {"ok": True, "result": result}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/nodes/{node_id}/collaborators/{collaborator_id}")
async def api_update_collaborator(
    node_id: str, collaborator_id: str, body: CollaboratorUpdateBody
) -> dict[str, Any]:
    try:
        await _auth()
        result = await users.update_collaborator(node_id, collaborator_id, body.role)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.delete("/nodes/{node_id}/collaborators/{collaborator_id}")
async def api_remove_collaborator(node_id: str, collaborator_id: str) -> dict[str, Any]:
    try:
        await _auth()
        result = await users.remove_collaborator(node_id, collaborator_id)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/users")
async def api_list_users() -> list[dict[str, Any]]:
    try:
        await _auth()
        return await users.list_users()
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/users/search")
async def api_search_users(q: str = Query("")) -> list[dict[str, Any]]:
    try:
        await _auth()
        return await users.search_users(q)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/users")
async def api_invite_users(body: InviteUsersBody) -> dict[str, Any]:
    try:
        await _auth()
        return await users.invite_users(body.users)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/users/{user_id}/role")
async def api_update_user_role(user_id: str, body: UpdateUserRoleBody) -> dict[str, Any]:
    try:
        await _auth()
        result = await users.update_user_role(user_id, body.role)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise _http_error(exc) from exc
