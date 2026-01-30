"""FastMCP server setup and lifecycle management for Salesforce MCP."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

import msgspec
from dotenv import load_dotenv
from fastmcp import FastMCP

from .logging_config import get_logger, setup_logging
from .oauth.storage import create_storage
from .oauth.token_verifier import SalesforceTokenVerifier
from .salesforce.client_manager import SalesforceClientManager
from .tools import (
    register_bulk_tools,
    register_metadata_tools,
    register_query_tools,
    register_record_tools,
)

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthConfig

load_dotenv()
setup_logging()

logger = get_logger("server")


class ServerConfig(msgspec.Struct, kw_only=True):
    """Server configuration."""

    client_id: str
    client_secret: str | None = None
    login_url: str = "https://login.salesforce.com"
    instance_url: str = "https://login.salesforce.com"
    # HTTP server settings
    transport: str = "stdio"
    base_url: str = "http://localhost:8000"
    port: int = 8000


class AppContext(msgspec.Struct, kw_only=True):
    """Application context shared across requests."""

    client_manager: SalesforceClientManager
    config: ServerConfig


def get_config() -> ServerConfig:
    """Load configuration from environment variables."""
    client_id = os.getenv("SALESFORCE_CLIENT_ID", "")
    client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")
    login_url = os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")
    instance_url = os.getenv("SALESFORCE_INSTANCE_URL", "https://login.salesforce.com")

    # HTTP server settings
    port = int(os.getenv("FASTMCP_PORT", "8000"))
    base_url = os.getenv("FASTMCP_BASE_URL", f"http://localhost:{port}")

    if client_id:
        logger.info("Client ID configured for OAuth")
    else:
        logger.warning("No SALESFORCE_CLIENT_ID configured")

    logger.debug(
        "Loaded config: login_url=%s, instance_url=%s",
        login_url,
        instance_url,
    )

    return ServerConfig(
        client_id=client_id,
        client_secret=client_secret,
        login_url=login_url,
        instance_url=instance_url,
        port=port,
        base_url=base_url,
    )


@asynccontextmanager
async def app_lifespan(mcp: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle and shared resources.

    This context manager initializes all shared resources on startup
    and cleans them up on shutdown.
    """
    logger.info("Starting Salesforce MCP Server")
    config = get_config()

    client_manager = SalesforceClientManager()

    ctx = AppContext(
        client_manager=client_manager,
        config=config,
    )

    try:
        logger.info("Server initialization complete")
        yield ctx
    finally:
        logger.info("Shutting down Salesforce MCP Server")
        await client_manager.clear_all_clients()
        logger.info("Server shutdown complete")


def _create_http_auth(config: ServerConfig) -> "AuthConfig":
    """Create auth configuration for HTTP mode with full OAuth support.

    Uses OAuthProxy to provide Dynamic Client Registration (DCR) for MCP clients
    like Gemini CLI that expect to register dynamically. The proxy presents a
    DCR-compliant interface while using pre-registered Salesforce Connected App
    credentials.

    Args:
        config: Server configuration

    Returns:
        OAuthProxy configured for Salesforce OAuth
    """
    from fastmcp.server.auth import OAuthProxy

    logger.info("Configuring HTTP auth with OAuthProxy for Salesforce")

    # OAuthProxy requires upstream_client_secret in constructor,
    # but with token_endpoint_auth_method="none", it won't be sent.
    # Use actual secret if available, or placeholder for PKCE-only.
    client_secret = config.client_secret or "pkce-only-no-secret"

    # Create storage backend based on environment configuration
    storage = create_storage()
    storage_type = os.getenv("OAUTH_STORAGE_TYPE", "memory")
    logger.info("Using %s storage for OAuth client data", storage_type)

    # Redirect URI configuration
    redirect_path = os.getenv("OAUTH_REDIRECT_PATH", "/auth/callback")

    # Optional: restrict allowed client redirect URIs
    allowed_uris_str = os.getenv("OAUTH_ALLOWED_CLIENT_REDIRECT_URIS")
    allowed_client_redirect_uris = (
        [uri.strip() for uri in allowed_uris_str.split(",")]
        if allowed_uris_str
        else None
    )

    logger.info("OAuth redirect path: %s", redirect_path)

    return OAuthProxy(
        # Salesforce OAuth endpoints
        upstream_authorization_endpoint=f"{config.login_url}/services/oauth2/authorize",
        upstream_token_endpoint=f"{config.login_url}/services/oauth2/token",
        # Salesforce Connected App credentials
        upstream_client_id=config.client_id,
        upstream_client_secret=client_secret,
        # Token verifier (validates upstream Salesforce tokens)
        token_verifier=SalesforceTokenVerifier(),
        # MCP server configuration
        base_url=config.base_url,
        redirect_path=redirect_path,
        allowed_client_redirect_uris=allowed_client_redirect_uris,
        # Forward PKCE to Salesforce
        forward_pkce=True,
        # PKCE-only: "none" = public client, no client_secret sent
        # Use "client_secret_post" if your Connected App requires secret
        token_endpoint_auth_method="none"
        if not config.client_secret
        else "client_secret_post",
        # Valid scopes for Salesforce
        valid_scopes=["api", "refresh_token", "offline_access"],
        # Storage backend for OAuth client data
        client_storage=storage,
    )


def create_server(transport: str = "stdio") -> FastMCP:
    """Create and configure the FastMCP server.

    Args:
        transport: Transport mode ('stdio' or 'streamable-http')

    Returns:
        Configured FastMCP server instance
    """
    logger.debug("Creating FastMCP server instance for transport: %s", transport)

    config = get_config()

    # Configure auth for HTTP mode
    auth: "AuthConfig | None" = None
    if transport == "streamable-http":
        auth = _create_http_auth(config)

    mcp = FastMCP(
        "Salesforce MCP Server",
        lifespan=app_lifespan,
        auth=auth,
    )

    logger.debug("Registering query tools")
    register_query_tools(mcp)
    logger.debug("Registering record tools")
    register_record_tools(mcp)
    logger.debug("Registering metadata tools")
    register_metadata_tools(mcp)
    logger.debug("Registering bulk tools")
    register_bulk_tools(mcp)

    logger.debug("Server creation complete")
    return mcp


# Default server for stdio mode (import compatibility)
mcp = create_server("stdio")


def main() -> None:
    """Main entry point for the server."""
    transport = "stdio"
    if len(sys.argv) > 1:
        transport = sys.argv[1]

    logger.info("Starting server with transport: %s", transport)

    # Create server with appropriate transport configuration
    server = create_server(transport)

    # Get port from environment
    port = int(os.getenv("FASTMCP_PORT", "8000"))

    try:
        if transport == "streamable-http":
            server.run(transport="streamable-http", port=port)
        else:
            server.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
