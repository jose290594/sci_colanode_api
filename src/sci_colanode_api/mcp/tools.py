from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from sci_colanode_api import __version__
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
from sci_colanode_api.sidecar import ensure_sidecar, get_sidecar


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def create_mcp() -> MCPServer:
    mcp = MCPServer(name="sci-colanode", version=__version__)

    @mcp.tool()
    async def colanode_list_workspaces() -> str:
        """List Colanode workspaces available to the service account."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await workspaces.list_workspaces())

    @mcp.tool()
    async def colanode_list_spaces() -> str:
        """List spaces in the current workspace."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await spaces.list_spaces())

    @mcp.tool()
    async def colanode_create_space(name: str, description: str | None = None) -> str:
        """Create a new space (and a Home page)."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await spaces.create_space(name, description=description))

    @mcp.tool()
    async def colanode_list_children(parent_id: str, node_type: str | None = None) -> str:
        """List child nodes under a parent. Optional node_type filter."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await nodes.list_children(parent_id, node_type=node_type))

    @mcp.tool()
    async def colanode_get_node(node_id: str) -> str:
        """Get a single node by id."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        node = await nodes.get_node(node_id)
        if node is None:
            return _json({"error": "not_found", "nodeId": node_id})
        return _json(node)

    @mcp.tool()
    async def colanode_get_tree(root_id: str, depth: int = 3) -> str:
        """Walk the node tree starting at root_id up to depth levels."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await nodes.get_tree(root_id, depth=depth))

    @mcp.tool()
    async def colanode_create_folder(parent_id: str, name: str) -> str:
        """Create a folder under a parent node."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await folders.create_folder(parent_id, name))

    @mcp.tool()
    async def colanode_list_databases(space_id: str | None = None) -> str:
        """List databases, optionally under a space."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await databases.list_databases(space_id))

    @mcp.tool()
    async def colanode_get_database_schema(database_id: str) -> str:
        """Get database field schema (ids, names, types)."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await databases.get_database_schema(database_id))

    @mcp.tool()
    async def colanode_list_records(database_id: str) -> str:
        """List records in a database."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await records.list_records(database_id))

    @mcp.tool()
    async def colanode_get_record(record_id: str) -> str:
        """Get a record by id."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await records.get_record(record_id))

    @mcp.tool()
    async def colanode_create_record(
        database_id: str,
        name: str,
        fields_json: str | None = None,
    ) -> str:
        """Create a record. fields_json is a JSON object of fieldName/fieldId -> value."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        fields = json.loads(fields_json) if fields_json else None
        return _json(await records.create_record(database_id, name, fields))

    @mcp.tool()
    async def colanode_update_record(
        record_id: str,
        name: str | None = None,
        fields_json: str | None = None,
    ) -> str:
        """Update a record name and/or fields (partial). fields_json is JSON object."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        fields = json.loads(fields_json) if fields_json else None
        return _json(await records.update_record(record_id, name=name, fields=fields))

    @mcp.tool()
    async def colanode_create_page(parent_id: str, name: str) -> str:
        """Create a page under a parent (space/folder/page)."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await pages.create_page(parent_id, name))

    @mcp.tool()
    async def colanode_get_page(page_id: str) -> str:
        """Get page attributes and document content."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await pages.get_page(page_id))

    @mcp.tool()
    async def colanode_update_page_content(page_id: str, content: str) -> str:
        """Update page body. Pass plain text or a JSON rich_text object string."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        payload: Any
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = content
        return _json(await pages.update_page_content(page_id, payload))

    @mcp.tool()
    async def colanode_rename_page(page_id: str, name: str) -> str:
        """Rename a page."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await pages.rename_page(page_id, name))

    @mcp.tool()
    async def colanode_delete_node(node_id: str) -> str:
        """Delete a node by id."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await nodes.delete_node(node_id))

    @mcp.tool()
    async def colanode_update_space(
        space_id: str,
        name: str | None = None,
        description: str | None = None,
        visibility: str | None = None,
    ) -> str:
        """Update a space name, description and/or visibility."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(
            await spaces.update_space(
                space_id, name=name, description=description, visibility=visibility
            )
        )

    @mcp.tool()
    async def colanode_rename_node(node_id: str, name: str) -> str:
        """Rename a node (space, folder, page, channel, database, …)."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await nodes.rename_node(node_id, name))

    @mcp.tool()
    async def colanode_reorder_space_child(
        space_id: str,
        child_id: str,
        after: str | None = None,
    ) -> str:
        """Reorder a child under a space. after=null moves it first."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await spaces.reorder_space_child(space_id, child_id, after=after))

    @mcp.tool()
    async def colanode_upload_file(
        parent_id: str,
        name: str,
        content_base64: str,
        mime_type: str | None = None,
    ) -> str:
        """Upload a file into a folder/space. content_base64 is the file body."""
        import base64

        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        data = base64.b64decode(content_base64)
        return _json(await files.upload_file(parent_id, name, data, mime_type=mime_type))

    @mcp.tool()
    async def colanode_download_file(file_id: str) -> str:
        """Download a file as base64. Files larger than 5MB should use REST download."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await files.download_file_payload(file_id))

    @mcp.tool()
    async def colanode_create_database(space_id: str, name: str) -> str:
        """Create a database with a default table view and Comment field."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await databases.create_database(space_id, name))

    @mcp.tool()
    async def colanode_add_field(
        database_id: str,
        name: str,
        field_type: str,
        relation_database_id: str | None = None,
        options_json: str | None = None,
    ) -> str:
        """Add a field to a database. options_json is a JSON list of {name,color} for select fields."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        options = json.loads(options_json) if options_json else None
        return _json(
            await databases.add_field(
                database_id,
                name,
                field_type,
                relation_database_id=relation_database_id,
                options=options,
            )
        )

    @mcp.tool()
    async def colanode_update_field(
        database_id: str,
        field_id: str,
        name: str | None = None,
        options_json: str | None = None,
        relation_database_id: str | None = None,
    ) -> str:
        """Update a database field name/options."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        options = json.loads(options_json) if options_json else None
        return _json(
            await databases.update_field(
                database_id,
                field_id,
                name=name,
                options=options,
                relation_database_id=relation_database_id,
            )
        )

    @mcp.tool()
    async def colanode_delete_field(database_id: str, field_id: str) -> str:
        """Delete a field from a database."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await databases.delete_field(database_id, field_id))

    @mcp.tool()
    async def colanode_list_views(database_id: str) -> str:
        """List database views."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await databases.list_views(database_id))

    @mcp.tool()
    async def colanode_create_view(
        database_id: str,
        name: str,
        layout: str = "table",
    ) -> str:
        """Create a database view (table, board, or calendar)."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await databases.create_view(database_id, name, layout=layout))

    @mcp.tool()
    async def colanode_search_records(database_id: str, search_query: str) -> str:
        """Search records in a database by text."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await records.search_records(database_id, search_query))

    @mcp.tool()
    async def colanode_delete_record(record_id: str) -> str:
        """Delete a database record."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await records.delete_record(record_id))

    @mcp.tool()
    async def colanode_create_channel(space_id: str, name: str) -> str:
        """Create a channel in a space."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await chat.create_channel(space_id, name))

    @mcp.tool()
    async def colanode_list_messages(parent_id: str) -> str:
        """List messages in a channel or chat."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await chat.list_messages(parent_id))

    @mcp.tool()
    async def colanode_send_message(
        parent_id: str,
        text: str,
        reference_id: str | None = None,
    ) -> str:
        """Send a plain-text message to a channel or chat."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await chat.send_message(parent_id, text=text, reference_id=reference_id))

    @mcp.tool()
    async def colanode_create_chat(collaborator_id: str) -> str:
        """Create a DM chat with another user."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await chat.create_chat(collaborator_id))

    @mcp.tool()
    async def colanode_list_collaborators(node_id: str) -> str:
        """List collaborators on a node (usually a space)."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await users.list_collaborators(node_id))

    @mcp.tool()
    async def colanode_add_collaborators(
        node_id: str,
        collaborator_ids_json: str,
        role: str = "editor",
    ) -> str:
        """Add collaborators. collaborator_ids_json is a JSON array of user ids."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        ids = json.loads(collaborator_ids_json)
        return _json(await users.add_collaborators(node_id, ids, role=role))

    @mcp.tool()
    async def colanode_update_collaborator(
        node_id: str,
        collaborator_id: str,
        role: str,
    ) -> str:
        """Update a collaborator role on a node."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await users.update_collaborator(node_id, collaborator_id, role))

    @mcp.tool()
    async def colanode_remove_collaborator(node_id: str, collaborator_id: str) -> str:
        """Remove a collaborator from a node."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await users.remove_collaborator(node_id, collaborator_id))

    @mcp.tool()
    async def colanode_list_users() -> str:
        """List workspace users."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await users.list_users())

    @mcp.tool()
    async def colanode_search_users(search_query: str) -> str:
        """Search workspace users by name/email."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await users.search_users(search_query))

    @mcp.tool()
    async def colanode_invite_users(users_json: str) -> str:
        """Invite users. users_json is [{email, role}, ...]."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        payload = json.loads(users_json)
        return _json(await users.invite_users(payload))

    @mcp.tool()
    async def colanode_update_user_role(user_id: str, role: str) -> str:
        """Update a workspace user's role (owner/admin/collaborator/guest/none)."""
        await ensure_sidecar()
        await get_sidecar().ensure_auth()
        return _json(await users.update_user_role(user_id, role))

    return mcp
