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

from .context import set_client_manager
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

    # Register in contextvar for module-level access
    set_client_manager(client_manager)

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


def _mask_secret(value: str | None) -> str:
    """Mask sensitive values for display."""
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def _print_config(transport: str, port: int) -> None:
    """Print server configuration at startup."""
    oauth_mode = _get_oauth_mode()
    client_id = os.getenv("SALESFORCE_CLIENT_ID")
    client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")
    storage_type = os.getenv("OAUTH_STORAGE_TYPE", "memory").lower()
    redis_url = os.getenv("REDIS_URL")

    # Build configuration sections
    sections: list[tuple[str, list[tuple[str, str]]]] = [
        (
            "Server",
            [
                ("Transport", transport),
                ("Port", str(port)),
                ("Log Level", os.getenv("LOG_LEVEL", "INFO")),
            ],
        ),
        (
            "Salesforce",
            [
                (
                    "Login URL",
                    os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com"),
                ),
                (
                    "Instance URL",
                    os.getenv(
                        "SALESFORCE_INSTANCE_URL", "https://login.salesforce.com"
                    ),
                ),
            ],
        ),
    ]

    # OAuth section (HTTP mode only)
    if transport == "http":
        oauth_items: list[tuple[str, str]] = [
            ("Mode", oauth_mode),
        ]

        if oauth_mode == "proxy":
            oauth_items.extend(
                [
                    ("Client ID", client_id or "(not set)"),
                    ("Client Secret", _mask_secret(client_secret)),
                    ("Scopes", os.getenv("OAUTH_REQUIRED_SCOPES", "(not set)")),
                    ("Redirect Path", os.getenv("OAUTH_REDIRECT_PATH", "/auth/callback")),
                    ("Base URL", os.getenv("BASE_URL") or "(not set)"),
                ]
            )

        sections.append(("OAuth", oauth_items))

        # Storage section (proxy mode only)
        if oauth_mode == "proxy":
            storage_items: list[tuple[str, str]] = [
                ("Type", storage_type),
            ]
            if storage_type == "redis":
                storage_items.append(("Redis URL", redis_url or "(not set)"))
            storage_items.append(
                (
                    "Encryption",
                    "enabled" if os.getenv("STORAGE_ENCRYPTION_KEY") else "disabled",
                )
            )
            sections.append(("Storage", storage_items))

    # Print configuration
    logger.info("")
    logger.info("=" * 55)
    logger.info("  Salesforce MCP Server Configuration")
    logger.info("=" * 55)

    for section_name, items in sections:
        logger.info("")
        logger.info("  [%s]", section_name)
        for key, value in items:
            logger.info("    %-20s %s", key, value)

    logger.info("")
    logger.info("=" * 55)

    # Print warnings for missing required values
    warnings: list[str] = []

    if transport == "http" and oauth_mode == "proxy":
        if not client_id:
            warnings.append("SALESFORCE_CLIENT_ID is required for proxy mode")
        if not os.getenv("BASE_URL"):
            warnings.append("BASE_URL should be set for OAuth callbacks")
        if storage_type == "redis" and not redis_url:
            warnings.append("REDIS_URL is required when OAUTH_STORAGE_TYPE=redis")

    for warning in warnings:
        logger.warning("  ⚠ %s", warning)

    if warnings:
        logger.info("")


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
    _print_config(transport, port)
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
