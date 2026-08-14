# SCI Colanode Bridge

**v0.0.1** · internal tooling by SCI Marketing

Python **REST + MCP** bridge to a self-hosted [Colanode](https://github.com/colanode/colanode) server. A Node **sidecar** runs `@colanode/client` locally for Yjs/CRDT mutations, file uploads (TUS), and sync.

```text
Cursor / automation          Admin browser
       │  Bearer sc_mcp_…            │ cookie session
       ▼                             ▼
  FastAPI bridge (:8786) ──► Node sidecar (:3921)
       │                             │
       └── /v1 REST, /mcp/ MCP       └── per-account Colanode client + SQLite
```

## Features

- **Multi-account** — each `sc_mcp_…` API key maps to one Colanode login (server URL + email + password).
- **Admin UI** at `/admin` — bootstrap master account, manage accounts and keys, copy MCP snippets.
- **MCP tools** — spaces, tree, pages, folders, files, databases, records, channels, collaborators, users.
- **REST mirror** under `/v1` (multipart upload, file download for large blobs).
- **Docker** — single image clones Colanode **v0.4.7** at build time; persistent `/data` volume.

## Requirements

- Python **3.10+**
- Node **22+** (local dev sidecar)
- Git (to clone Colanode into `vendor/colanode` for local dev)

## Quick start (local)

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\python -m pip install -e ".[dev]"
# macOS / Linux
# pip install -e ".[dev]"

git clone --depth 1 --branch v0.4.7 https://github.com/colanode/colanode.git vendor/colanode
cd vendor/colanode && npm install --ignore-scripts --engine-strict=false && cd ../..
cd sidecar && npm install --engine-strict=false && cd ..

cp .env.example .env
# Edit BRIDGE_SECRET (32+ random bytes) and PUBLIC_BASE_URL (http://127.0.0.1:8786 locally)

python -m sci_colanode_api.main
```

1. Open **http://127.0.0.1:8786/admin**
2. Create the **master** account (Colanode config URL, email, password, optional default workspace).
3. Copy the generated **`sc_mcp_…`** key and MCP snippet.

Colanode credentials live in **`data/store.json`** (encrypted). They are **not** read from `.env` at runtime once bootstrapped.

### Dev helper (Windows)

```bat
scripts\dev.bat
```

Starts the sidecar in a separate window, then the API.

### Smoke test

With at least one account in the store:

```bash
python scripts/smoke_login.py
```

## Cursor MCP

Use a **trailing slash** on `/mcp/` (redirects may strip `Authorization` without it):

```json
{
  "mcpServers": {
    "sci-colanode": {
      "url": "https://your-bridge.example.com/mcp/",
      "headers": { "Authorization": "Bearer sc_mcp_…" }
    }
  }
}
```

## Docker

```bash
export BRIDGE_SECRET="$(openssl rand -hex 32)"
export PUBLIC_BASE_URL="https://colanode-mcp.example.com"
docker compose up -d --build
```

| Item | Value |
|------|--------|
| HTTP port | **8786** |
| Data volume | `bridge-data` → `/data` (store + sidecar state) |
| First setup | `https://<host>/admin` |

Put HTTPS (Caddy, nginx, OpenResty) in front. Set `PUBLIC_BASE_URL` to the public origin **without** a path prefix. If you mount the app under a subpath, strip the prefix at the proxy and keep `PUBLIC_BASE_URL` as the external origin.

## Configuration

| Variable | Purpose |
|----------|---------|
| `BRIDGE_SECRET` | Admin session signing + Fernet key for Colanode passwords |
| `PUBLIC_BASE_URL` | Origin used in MCP snippets from `/admin` |
| `BRIDGE_HOST` / `BRIDGE_PORT` | Listen address (`0.0.0.0:8786` in Docker) |
| `COLANODE_DATA_DIR` | Runtime dir (`./data` local, `/data` Docker) |
| `COLANODE_ASSETS_DIR` | Colanode assets (optional; Docker sets this) |
| `SIDECAR_*` | Sidecar bind URL/port and auto-start |
| `MCP_DNS_REBINDING_PROTECTION` | Default `false`; enable only with Host allowlists |
| `SC_ACCOUNT_ID` | Optional account for MCP **stdio** mode |

See `.env.example` for defaults.

## Admin model

1. **Empty store** → bootstrap form creates the **master** account and one API key.
2. **Master login** → manage all accounts, rotate any keys.
3. **Non-master login** → edit only that account and its keys.

Passwords: bcrypt (admin login) + Fernet (Colanode password for the sidecar). Fernet derives from `BRIDGE_SECRET`, or from auto-generated `data/.bridge_secret` when `BRIDGE_SECRET` is unset (local only).

## REST

All `/v1/*` routes require `Authorization: Bearer sc_mcp_…`.

```bash
curl -sS -H "Authorization: Bearer $SC_MCP_KEY" "$PUBLIC_BASE_URL/v1/spaces"
```

Notable routes:

- `POST /v1/nodes/{parent_id}/files` — multipart upload
- `GET /v1/files/{id}/download` — download (preferred for files &gt; 5 MB)

OpenAPI: `/docs`

## MCP tools

| Area | Tools |
|------|--------|
| Workspaces | `colanode_list_workspaces` |
| Spaces | `colanode_list_spaces`, `colanode_create_space`, `colanode_update_space`, `colanode_reorder_space_child` |
| Tree | `colanode_list_children`, `colanode_get_node`, `colanode_get_tree`, `colanode_rename_node`, `colanode_delete_node` |
| Folders | `colanode_create_folder` |
| Files | `colanode_upload_file`, `colanode_download_file` (base64; size cap 5 MB) |
| Databases | `colanode_list_databases`, `colanode_create_database`, `colanode_get_database_schema`, `colanode_add_field`, `colanode_update_field`, `colanode_delete_field`, `colanode_list_views`, `colanode_create_view` |
| Records | `colanode_list_records`, `colanode_create_record`, `colanode_update_record`, `colanode_search_records`, `colanode_delete_record` |
| Pages | `colanode_create_page`, `colanode_get_page`, `colanode_update_page_content`, `colanode_rename_page` |
| Chat | `colanode_create_channel`, `colanode_list_messages`, `colanode_send_message`, `colanode_create_chat` |
| Access | `colanode_list_collaborators`, `colanode_add_collaborators`, `colanode_update_collaborator`, `colanode_remove_collaborator` |
| Users | `colanode_list_users`, `colanode_search_users`, `colanode_invite_users`, `colanode_update_user_role` |

Uploads wait until the file node reaches **Ready** (TUS to Colanode). Keep the sidecar running until uploads finish.

### Known limitations (v0.0.1)

- `colanode_search_records` / `colanode_search_users` need the sidecar FTS index (`node_names`); on a fresh data dir, fall back to list + filter.
- Space child order from `colanode_list_children` may not reflect `colanode_reorder_space_child` until Colanode exposes sort in list queries.

## Security

**Never commit:**

- `.env`, `data/`, `data/store.json`, `data/.bridge_secret`
- API keys, Colanode passwords, or live workspace/node IDs in scripts

**Operational:**

- Use HTTPS and a strong `BRIDGE_SECRET` before exposing the bridge.
- One Colanode user (or scoped role) per API key where possible.
- Rotate leaked `sc_mcp_…` keys from `/admin`.
- This service is separate from the Colanode server; treat it as a privileged automation layer.

## Development

Active branch: **`development`**.

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

Colanode pin: **v0.4.7** (see `vendor/README.md` and `Dockerfile`).

## License

Proprietary — SCI Marketing. All rights reserved.
