# Salesforce MCP Server

[![Release](https://img.shields.io/github/v/release/hypn4/salesforce-mcp-server)](https://github.com/hypn4/salesforce-mcp-server/releases)
[![Container](https://img.shields.io/badge/Container-ghcr.io-blue)](https://ghcr.io/hypn4/salesforce-mcp-server)

A Model Context Protocol (MCP) server that provides Salesforce integration for AI agents with flexible OAuth authentication.

## Features

- **Dual OAuth modes** - Bearer token validation or full OAuth 2.1 proxy
- **16 MCP tools** across 4 categories for comprehensive Salesforce operations
- **Per-user Salesforce client caching** - Efficient connection management
- **Dual transport modes** - STDIO for local clients, HTTP for multi-user deployments
- **RFC-compliant OAuth** - RFC 8414, RFC 9728, RFC 7591, PKCE support
- **Client OAuth flexibility** - ADK agents, Claude Code, Gemini CLI all supported

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

### Option 1: uvx (Recommended)

```bash
uvx salesforce-mcp-server --transport stdio
# or for HTTP mode:
uvx salesforce-mcp-server --transport http
```

### Option 2: Docker

```bash
docker pull ghcr.io/hypn4/salesforce-mcp-server

# HTTP mode (default)
docker run -p 8000:8000 \
  -e SALESFORCE_CLIENT_ID=your_client_id \
  -e SALESFORCE_LOGIN_URL=https://login.salesforce.com \
  ghcr.io/hypn4/salesforce-mcp-server

# STDIO mode
docker run -i \
  -e SALESFORCE_ACCESS_TOKEN=your_token \
  -e SALESFORCE_INSTANCE_URL=https://your-domain.my.salesforce.com \
  ghcr.io/hypn4/salesforce-mcp-server --transport stdio
```

### Option 3: Pre-built Binary

Download from [GitHub Releases](https://github.com/hypn4/salesforce-mcp-server/releases):

| Platform | Download |
|----------|----------|
| Linux (x64) | `salesforce-mcp-server-linux-amd64.tar.gz` |
| Linux (ARM64) | `salesforce-mcp-server-linux-arm64.tar.gz` |
| macOS (ARM64) | `salesforce-mcp-server-darwin-arm64.tar.gz` |
| Windows (x64) | `salesforce-mcp-server-windows-amd64.zip` |

Verify checksum:
```bash
# Download checksums-sha256.txt from the release
sha256sum -c checksums-sha256.txt
```

### Option 4: From Source

```bash
git clone https://github.com/hypn4/salesforce-mcp-server.git
cd salesforce-mcp-server
cp .env.example .env
# Edit .env with your Salesforce credentials
uv sync
```

## Configuration

All configuration is done through environment variables. Copy `.env.example` to `.env` and adjust as needed.

### OAuth Mode

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_MODE` | `bearer` | `bearer` for client-handled OAuth, `proxy` for server OAuth proxy |

#### Bearer Mode (Default)

Clients handle OAuth themselves. The server validates Bearer tokens via Salesforce userinfo endpoint.

| Variable | Default | Description |
|----------|---------|-------------|
| `SALESFORCE_INSTANCE_URL` | `https://login.salesforce.com` | Token verification URL |

#### Proxy Mode

Server acts as OAuth 2.1 + PKCE proxy to Salesforce. Provides RFC-compliant endpoints:
- `/.well-known/oauth-authorization-server` (RFC 8414)
- `/.well-known/oauth-protected-resource` (RFC 9728)
- `/register` (RFC 7591 Dynamic Client Registration)
- `/authorize`, `/token`, `/auth/callback` (OAuth 2.1 + PKCE)

| Variable | Required | Description |
|----------|----------|-------------|
| `SALESFORCE_CLIENT_ID` | Yes | Salesforce Connected App client ID |
| `SALESFORCE_CLIENT_SECRET` | No | Client secret (optional, see modes below) |
| `SALESFORCE_LOGIN_URL` | No | Login URL (default: `https://login.salesforce.com`) |
| `BASE_URL` | No | Public URL of the server (default: `http://localhost:8000`) |
| `OAUTH_REQUIRED_SCOPES` | No | Comma-separated scopes (default: `api,refresh_token`) |

**Authentication Modes**

| Mode | `SALESFORCE_CLIENT_SECRET` | Use Case |
|------|----------------------------|----------|
| **Confidential Client** | Set | Server-side apps where secret can be stored securely |
| **PKCE-only (Public Client)** | Empty/Unset | CLI tools, mobile apps, or when secret storage isn't possible |

For PKCE-only mode, configure your Salesforce Connected App:
- ✅ Enable "Require Proof Key for Code Exchange (PKCE)"
- ❌ Disable "Require Secret for Web Server Flow"

**Storage Configuration (Proxy Mode)**

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_STORAGE_TYPE` | `memory` | `memory` or `redis` |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `STORAGE_ENCRYPTION_KEY` | - | Fernet key for token encryption |

### HTTP Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | HTTP server port (cloud platform standard) |
| `FASTMCP_PORT` | - | HTTP server port (fallback, for backwards compatibility) |

> **Port Priority**: `PORT` → `FASTMCP_PORT` → `8000` (default)
>
> Cloud platforms (Heroku, Cloud Run, Railway, etc.) automatically set the `PORT` environment variable.

### Salesforce Instance

| Variable | Default | Description |
|----------|---------|-------------|
| `SALESFORCE_LOGIN_URL` | `https://login.salesforce.com` | For sandbox use `https://test.salesforce.com` |
| `SALESFORCE_INSTANCE_URL` | `https://login.salesforce.com` | Token verification URL (userinfo endpoint) |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## MCP Integration Guide

### Authentication Modes

This server supports two OAuth modes:

#### Bearer Token Mode (Default)

Standard MCP authentication pattern (like GitHub, Stripe MCP servers):

- **Server**: Validates Bearer tokens via Salesforce userinfo endpoint
- **Clients**: Handle OAuth authentication themselves

| Client Type | OAuth Handling |
|-------------|----------------|
| **ADK Agents** | Use `auth_scheme` + `auth_credential` in McpToolset |
| **Claude Desktop/Code/Gemini CLI** | Static access token via environment variables (STDIO Mode) |

#### OAuth Proxy Mode

Full OAuth 2.1 + PKCE proxy with RFC-compliant discovery:

- **Server**: Handles complete OAuth flow with Salesforce
- **Clients**: Use standard OAuth discovery (automatic with compatible clients)

| Client Type | OAuth Handling |
|-------------|----------------|
| **Claude Desktop** | Native OAuth discovery (automatic) |
| **Claude Code** | Native OAuth discovery (automatic) |
| **Gemini CLI** | Native OAuth discovery (automatic) |
| **ADK Agents** | StreamableHTTPConnectionParams with Bearer token |

To enable proxy mode:
```bash
export OAUTH_MODE=proxy
export SALESFORCE_CLIENT_ID=your_client_id
export BASE_URL=https://your-server.com

# Optional: Add client_secret for confidential client mode
# Omit for PKCE-only (public client) mode
export SALESFORCE_CLIENT_SECRET=your_client_secret
```

### Transport Modes

| Mode | Authentication | Use Case |
|------|----------------|----------|
| **STDIO** | Access Token (env vars) | Local development, single-user |
| **HTTP** | Bearer Token (Authorization header) | Multi-user, web-based clients |

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

**OAuth Proxy Mode (Recommended)**

Native OAuth 2.1 + PKCE - no additional tools required.

1. Configure the server for proxy mode:
```bash
export OAUTH_MODE=proxy
export SALESFORCE_CLIENT_ID=your_connected_app_client_id
export BASE_URL=http://localhost:8000
# Optional: SALESFORCE_CLIENT_SECRET for confidential client mode
```

2. Start the server:
```bash
uvx salesforce-mcp-server --transport http
```

3. Configure Claude Desktop:
```json
{
  "mcpServers": {
    "salesforce": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Claude Desktop will automatically discover OAuth endpoints and initiate authentication when you first use a Salesforce tool.

**STDIO Mode (Static Token)**

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "uvx",
      "args": ["salesforce-mcp-server", "--transport", "stdio"],
      "env": {
        "SALESFORCE_ACCESS_TOKEN": "00D...",
        "SALESFORCE_INSTANCE_URL": "https://your-domain.my.salesforce.com"
      }
    }
  }
}
```

---

### Claude Code

Config file location:
- Global: `~/.claude/settings.json`
- Project: `.mcp.json`

**OAuth Proxy Mode (Recommended)**

Native OAuth 2.1 + PKCE - no additional tools required.

1. Configure the server (see Configuration section above)

2. Start the server:
```bash
uvx salesforce-mcp-server --transport http
```

3. Add the MCP server:
```bash
claude mcp add salesforce --transport http http://localhost:8000/mcp
```

Or configure manually in `~/.claude/settings.json` or `.mcp.json`:
```json
{
  "mcpServers": {
    "salesforce": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Claude Code will automatically discover OAuth endpoints via RFC 8414 metadata.

**STDIO Mode (Static Token)**

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "uvx",
      "args": ["salesforce-mcp-server", "--transport", "stdio"],
      "env": {
        "SALESFORCE_ACCESS_TOKEN": "00D...",
        "SALESFORCE_INSTANCE_URL": "https://your-domain.my.salesforce.com"
      }
    }
  }
}
```

---

### Gemini CLI

Config file: `~/.gemini/settings.json`

**OAuth Proxy Mode (Recommended)**

Native OAuth discovery - Gemini CLI auto-discovers OAuth endpoints.

1. Configure the server (see Configuration section above)

2. Start the server:
```bash
uvx salesforce-mcp-server --transport http
```

3. Add the MCP server:
```bash
gemini mcp add salesforce http://localhost:8000/mcp
```

Or configure manually in `~/.gemini/settings.json`:
```json
{
  "mcpServers": {
    "salesforce": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Gemini CLI will automatically discover OAuth endpoints and initiate authentication.

**STDIO Mode (Static Token)**

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "uvx",
      "args": ["salesforce-mcp-server", "--transport", "stdio"],
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
uvx salesforce-mcp-server --transport stdio
# or with local development:
just run
```

**HTTP Mode:**
```bash
uvx salesforce-mcp-server --transport http
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
| `just docker-build` | Build Docker image |
| `just docker-run` | Run in Docker (HTTP mode) |
| `just docker-run-stdio` | Run in Docker (STDIO mode) |
| `just build-binary` | Build standalone binary |

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
│   ├── oauth/             # OAuth authentication
│   │   ├── proxy.py           # OAuth 2.1 proxy for Salesforce
│   │   ├── token_verifier.py  # Salesforce token validation
│   │   ├── token_access.py    # Token access utilities
│   │   ├── storage.py         # Token storage backends
│   │   └── pkce.py            # PKCE utilities
│   └── salesforce/        # Salesforce client
├── tests/
├── .env.example
├── justfile
└── pyproject.toml
```

## License

MIT
