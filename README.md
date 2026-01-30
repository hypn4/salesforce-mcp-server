# Salesforce MCP Server

A Model Context Protocol (MCP) server that provides Salesforce integration for AI agents with multi-user OAuth 2.0 PKCE authentication support.

## Features

- **Multi-user OAuth 2.0 with PKCE** - Secure authentication without storing client secrets
- **16 MCP tools** across 4 categories for comprehensive Salesforce operations
- **Per-user Salesforce client caching** - Efficient connection management
- **Configurable storage backend** - Memory (default) or Redis for production deployments
- **Optional Fernet encryption** - Encrypt stored OAuth data at rest
- **Dual transport modes** - STDIO for local clients, HTTP for web-based OAuth flows

### Available Tools

| Category | Tools |
|----------|-------|
| **Query** | `salesforce_query`, `salesforce_query_all`, `salesforce_query_more`, `salesforce_search` |
| **Records** | `salesforce_get_record`, `salesforce_create_record`, `salesforce_update_record`, `salesforce_delete_record`, `salesforce_upsert_record` |
| **Metadata** | `salesforce_describe_object`, `salesforce_list_objects`, `salesforce_get_object_fields` |
| **Bulk API** | `salesforce_bulk_query`, `salesforce_bulk_insert`, `salesforce_bulk_update`, `salesforce_bulk_delete` |

## Prerequisites

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) package manager
- Salesforce Connected App (see [Connected App Setup](#salesforce-connected-app-setup))

## Installation

```bash
git clone https://github.com/hypn4/salesforce-mcp-server.git
cd salesforce-mcp-server
cp .env.example .env
# Edit .env with your Salesforce credentials
uv sync
```

## Configuration

All configuration is done through environment variables. Copy `.env.example` to `.env` and adjust as needed.

### HTTP Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FASTMCP_PORT` | `8000` | HTTP server port |
| `FASTMCP_BASE_URL` | `http://localhost:8000` | Base URL for OAuth callbacks |

### OAuth Redirect Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_REDIRECT_PATH` | `/auth/callback` | OAuth callback path |
| `OAUTH_ALLOWED_CLIENT_REDIRECT_URIS` | (empty) | Comma-separated allowed client redirect URIs |

### Salesforce OAuth (Required)

| Variable | Required | Description |
|----------|----------|-------------|
| `SALESFORCE_CLIENT_ID` | Yes | Connected App Consumer Key |
| `SALESFORCE_CLIENT_SECRET` | No | Client secret (leave empty for PKCE-only) |

### Salesforce Instance

| Variable | Default | Description |
|----------|---------|-------------|
| `SALESFORCE_LOGIN_URL` | `https://login.salesforce.com` | Authorization server (use `https://test.salesforce.com` for sandbox) |
| `SALESFORCE_INSTANCE_URL` | `https://login.salesforce.com` | API calls and token verification URL |

### OAuth Storage Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_STORAGE_TYPE` | `memory` | Storage type: `memory` or `redis` |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL (if using redis) |
| `STORAGE_ENCRYPTION_KEY` | (empty) | Fernet encryption key for stored data |

Generate an encryption key with:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## MCP Integration Guide

### Transport Modes and Authentication

| Mode | Authentication | Use Case |
|------|----------------|----------|
| **STDIO** | Access Token (env vars) | Claude Desktop, Claude Code |
| **HTTP** | OAuth 2.0 PKCE | Gemini CLI, Web clients |

> **Note**: STDIO mode does not support OAuth flow.
> You must provide an Access Token via environment variables.

### STDIO Mode Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SALESFORCE_ACCESS_TOKEN` | Yes | Salesforce Access Token |
| `SALESFORCE_INSTANCE_URL` | Yes | Salesforce Instance URL (e.g., `https://your-domain.my.salesforce.com`) |
| `SALESFORCE_USER_ID` | No | User ID (default: `env_user`) |
| `SALESFORCE_ORG_ID` | No | Org ID (default: `env_org`) |
| `SALESFORCE_USERNAME` | No | Username (default: `env_user`) |

### Getting an Access Token for STDIO Mode

Use Salesforce CLI to get your Access Token:

```bash
sf org display --target-org <your-org-alias>
```

From the output, copy the `Access Token` and `Instance Url` values for your configuration.

---

### Claude Desktop

Config file location:
- macOS/Linux: `~/.config/claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**STDIO Mode (Recommended)**

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "uvx",
      "args": ["salesforce-mcp-server", "stdio"],
      "env": {
        "SALESFORCE_ACCESS_TOKEN": "00D...",
        "SALESFORCE_INSTANCE_URL": "https://your-domain.my.salesforce.com"
      }
    }
  }
}
```

**HTTP Mode**

First, start the server:
```bash
uvx salesforce-mcp-server streamable-http
```

Then configure Claude Desktop:
```json
{
  "mcpServers": {
    "salesforce": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

### Claude Code

Config file location:
- Global: `~/.claude/settings.json`
- Project: `.mcp.json`

**STDIO Mode (Recommended)**

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "uvx",
      "args": ["salesforce-mcp-server", "stdio"],
      "env": {
        "SALESFORCE_ACCESS_TOKEN": "00D...",
        "SALESFORCE_INSTANCE_URL": "https://your-domain.my.salesforce.com"
      }
    }
  }
}
```

**HTTP Mode**

First, start the server:
```bash
uvx salesforce-mcp-server streamable-http
```

Then configure Claude Code:
```json
{
  "mcpServers": {
    "salesforce": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

### Gemini CLI

Config file: `~/.gemini/settings.json`

**HTTP Mode with OAuth (Recommended)**

First, start the server with environment variables:
```bash
SALESFORCE_CLIENT_ID=your_client_id \
SALESFORCE_LOGIN_URL=https://login.salesforce.com \
SALESFORCE_INSTANCE_URL=https://your-domain.my.salesforce.com \
uvx salesforce-mcp-server streamable-http
```

Then configure Gemini CLI:
```json
{
  "mcpServers": {
    "salesforce": {
      "httpUrl": "http://localhost:8000/mcp",
      "authProvider": "dynamic_discovery"
    }
  }
}
```

Gemini CLI uses HTTP mode with OAuth 2.0 Dynamic Client Registration. The OAuth flow is handled automatically when you first use a Salesforce tool.

**STDIO Mode**

> **Warning**: STDIO mode does not support OAuth. You must provide an Access Token directly.
> Use HTTP Mode above if you need OAuth authentication.

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "uvx",
      "args": ["salesforce-mcp-server", "stdio"],
      "env": {
        "SALESFORCE_ACCESS_TOKEN": "00D...",
        "SALESFORCE_INSTANCE_URL": "https://your-domain.my.salesforce.com"
      }
    }
  }
}
```

---

### Running Manually

**STDIO Mode:**
```bash
uvx salesforce-mcp-server stdio
# or with local development:
just run
```

**HTTP Mode:**
```bash
uvx salesforce-mcp-server streamable-http
# or with local development:
just run-http
```

HTTP mode default endpoint: `http://localhost:8000`

## Salesforce Connected App Setup

1. In Salesforce Setup, navigate to **App Manager**
2. Click **New Connected App**
3. Fill in basic information (name, contact email)
4. Enable **OAuth Settings**
5. Set **Callback URL** to match your deployment:
   - For local development: `http://localhost:8000/auth/callback`
   - For production: `https://your-domain.com/auth/callback`
6. Select OAuth scopes:
   - `api` (Access and manage your data)
   - `refresh_token` (Perform requests at any time)
   - `offline_access` (Perform requests at any time)
7. Enable **Require Proof Key for Code Exchange (PKCE) Extension for Supported Authorization Flows**
8. Save and copy the **Consumer Key** (this is your `SALESFORCE_CLIENT_ID`)

## Available Tools Reference

### Query Tools

| Tool | Description |
|------|-------------|
| `salesforce_query` | Execute a SOQL query against Salesforce |
| `salesforce_query_all` | Execute a SOQL query including deleted and archived records |
| `salesforce_query_more` | Fetch additional records from a paginated query result |
| `salesforce_search` | Execute a SOSL full-text search |

### Record Tools

| Tool | Description |
|------|-------------|
| `salesforce_get_record` | Get a single record by ID |
| `salesforce_create_record` | Create a new record |
| `salesforce_update_record` | Update an existing record |
| `salesforce_delete_record` | Delete a record |
| `salesforce_upsert_record` | Upsert a record using an external ID field |

### Metadata Tools

| Tool | Description |
|------|-------------|
| `salesforce_describe_object` | Get metadata for an SObject (fields, relationships, etc.) |
| `salesforce_list_objects` | List all available SObjects in the org |
| `salesforce_get_object_fields` | Get field information for an SObject |

### Bulk API Tools

| Tool | Description |
|------|-------------|
| `salesforce_bulk_query` | Execute a bulk query for large data sets (>2,000 records) |
| `salesforce_bulk_insert` | Insert multiple records efficiently |
| `salesforce_bulk_update` | Update multiple records efficiently |
| `salesforce_bulk_delete` | Delete multiple records efficiently |

## Development

### Commands

| Command | Description |
|---------|-------------|
| `just run` | Run server in STDIO mode |
| `just run-http` | Run server in HTTP mode |
| `just run-debug` | Run with DEBUG logging |
| `just test` | Run tests |
| `just test-cov` | Run tests with coverage |
| `just lint` | Run linter |
| `just lint-fix` | Run linter with auto-fix |
| `just fmt` | Format code |
| `just inspector` | Run with MCP Inspector for debugging |
| `just tools` | List all registered MCP tools |

### Project Structure

```
salesforce-mcp-server/
├── src/salesforce_mcp_server/
│   ├── server.py          # FastMCP server setup
│   ├── tools/             # MCP tool implementations
│   │   ├── query.py       # SOQL/SOSL query tools
│   │   ├── records.py     # Record CRUD tools
│   │   ├── metadata.py    # Metadata tools
│   │   └── bulk.py        # Bulk API tools
│   ├── oauth/             # OAuth handling
│   │   ├── storage.py     # Storage backends
│   │   └── token_*.py     # Token management
│   └── salesforce/        # Salesforce client
├── tests/
├── .env.example
├── justfile
└── pyproject.toml
```

## License

MIT
