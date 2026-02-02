"""FastMCP server setup and lifecycle management for Salesforce MCP."""

from __future__ import annotations

import asyncio
import os
import signal
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated, AsyncIterator

import msgspec
import typer
from dotenv import load_dotenv
from fastmcp import FastMCP

from .logging_config import get_logger, setup_logging
from .oauth.proxy import SalesforceOAuthProxy
from .oauth.token_verifier import SalesforceTokenVerifier
from .salesforce.client_manager import SalesforceClientManager
from .tools import (
    register_bulk_tools,
    register_metadata_tools,
    register_query_tools,
    register_record_tools,
)

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider

load_dotenv()
setup_logging()

logger = get_logger("server")


class ServerConfig(msgspec.Struct, kw_only=True):
    """Server configuration."""

    login_url: str = "https://login.salesforce.com"
    instance_url: str = "https://login.salesforce.com"
    # HTTP server settings
    port: int = 8000


class AppContext(msgspec.Struct, kw_only=True):
    """Application context shared across requests."""

    client_manager: SalesforceClientManager
    config: ServerConfig


def get_config() -> ServerConfig:
    """Load configuration from environment variables."""
    login_url = os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")
    instance_url = os.getenv("SALESFORCE_INSTANCE_URL", "https://login.salesforce.com")

    # HTTP server settings
    # Cloud platform standard: PORT first, then FASTMCP_PORT, then default
    port = int(os.getenv("PORT") or os.getenv("FASTMCP_PORT") or "8000")

    logger.debug(
        "Loaded config: login_url=%s, instance_url=%s, port=%d",
        login_url,
        instance_url,
        port,
    )

    return ServerConfig(
        login_url=login_url,
        instance_url=instance_url,
        port=port,
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


def _get_oauth_mode() -> str:
    """Get the OAuth mode from environment.

    Returns:
        str: 'proxy' for OAuth proxy mode, 'bearer' for Bearer token mode
    """
    return os.getenv("OAUTH_MODE", "bearer").lower()


def _create_http_auth() -> "AuthProvider":
    """Create auth configuration for HTTP mode.

    The auth mode is determined by OAUTH_MODE environment variable:

    - 'bearer' (default): Clients handle OAuth themselves, server validates
      Bearer tokens using Salesforce userinfo endpoint. Use with:
      - ADK agents: auth_scheme + auth_credential in McpToolset
      - Claude Code/Gemini CLI: mcp-remote with --static-oauth-client-info

    - 'proxy': Server acts as OAuth 2.1 proxy to Salesforce. Provides
      full RFC-compliant OAuth endpoints including:
      - /.well-known/oauth-authorization-server (RFC 8414)
      - /.well-known/oauth-protected-resource (RFC 9728)
      - /register (RFC 7591 Dynamic Client Registration)
      - /authorize, /token, /auth/callback (OAuth 2.1 + PKCE)

      Requires SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET.

    Returns:
        AuthProvider for the configured mode

    Raises:
        ValueError: If proxy mode is requested but credentials are not configured
    """
    oauth_mode = _get_oauth_mode()

    if oauth_mode == "proxy":
        logger.info("Configuring HTTP auth with OAuth Proxy mode")
        proxy = SalesforceOAuthProxy.from_env()
        if proxy is None:
            raise ValueError(
                "OAuth proxy mode requires SALESFORCE_CLIENT_ID environment variable. "
                "SALESFORCE_CLIENT_SECRET is optional (omit for PKCE-only mode)."
            )
        return proxy.oauth_proxy

    # Default: Bearer token mode
    logger.info("Configuring HTTP auth with Bearer token mode")
    return SalesforceTokenVerifier()


def create_server(transport: str = "stdio") -> FastMCP:
    """Create and configure the FastMCP server.

    Args:
        transport: Transport mode ('stdio' or 'http')

    Returns:
        Configured FastMCP server instance
    """
    logger.debug("Creating FastMCP server instance for transport: %s", transport)

    # Configure auth for HTTP mode
    auth: "AuthProvider | None" = None
    if transport == "http":
        auth = _create_http_auth()

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


async def run_server_async(transport: str, port: int) -> None:
    """Run the server with graceful shutdown support.

    Args:
        transport: Transport mode ('stdio' or 'http')
        port: Port number for HTTP transport
    """
    server = create_server(transport)

    def handle_shutdown(sig: signal.Signals) -> None:
        logger.info("Received signal %s, initiating shutdown...", sig.name)

    # Set up signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_shutdown, sig)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for SIGTERM
            pass

    logger.info("Starting server with transport: %s", transport)

    try:
        if transport == "http":
            await server.run_async(transport="http", port=port)
        else:
            await server.run_async(transport="stdio")
    except asyncio.CancelledError:
        logger.info("Server task cancelled")


app = typer.Typer(
    name="salesforce-mcp-server",
    help="Salesforce MCP Server - Model Context Protocol server for Salesforce.",
    add_completion=False,
)


@app.command()
def main(
    transport: Annotated[
        str,
        typer.Option(
            "--transport",
            "-t",
            help="Transport mode: stdio, http",
        ),
    ] = "stdio",
    port: Annotated[
        int | None,
        typer.Option(
            "--port",
            "-p",
            help="Port for HTTP transport (default: from PORT env or 8000)",
        ),
    ] = None,
) -> None:
    """Run the Salesforce MCP Server."""
    actual_port = port or int(os.getenv("PORT") or os.getenv("FASTMCP_PORT") or "8000")

    try:
        asyncio.run(run_server_async(transport, actual_port))
    except KeyboardInterrupt:
        # Fallback for platforms where signal handlers don't work
        logger.info("Server stopped by user")


if __name__ == "__main__":
    app()
