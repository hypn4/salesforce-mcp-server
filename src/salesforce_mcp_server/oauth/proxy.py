"""Salesforce OAuth Proxy for FastMCP.

This module provides a wrapper around FastMCP's OAuthProxy that is
pre-configured for Salesforce Connected App integration. It handles:

- OAuth 2.1 + PKCE (forwarded to Salesforce)
- Dynamic Client Registration (RFC 7591)
- Authorization Server Metadata (RFC 8414)
- Protected Resource Metadata (RFC 9728)
- Token issuance and upstream token storage

Supports two modes:
- Confidential Client: Uses client_secret + PKCE (more secure)
- PKCE-only (Public Client): Uses only PKCE, no client_secret required
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastmcp.server.auth import OAuthProxy

from ..logging_config import get_logger
from .storage import create_storage
from .token_verifier import SalesforceTokenVerifier

if TYPE_CHECKING:
    from key_value.aio.protocols.key_value import AsyncKeyValue

logger = get_logger("oauth.proxy")


class SalesforceOAuthProxy:
    """OAuth Proxy wrapper for Salesforce Connected App integration.

    This class creates a FastMCP OAuthProxy configured to work with
    Salesforce OAuth endpoints. It acts as a transparent proxy that:

    1. Accepts OAuth requests from MCP clients (Claude Code, Gemini CLI, ADK)
    2. Proxies authorization to Salesforce with PKCE
    3. Stores upstream Salesforce tokens encrypted
    4. Issues FastMCP JWT tokens to clients

    Architecture:
        MCP Client → OAuth Proxy → Salesforce OAuth
                   ↓
        MCP Client ← JWT Token (FastMCP) ← Upstream Token (Salesforce)

    Modes:
        Confidential Client (client_secret provided):
            - Uses client_secret_post authentication
            - PKCE forwarded for additional security
            - Salesforce: "Require Secret for Web Server Flow" enabled

        PKCE-only / Public Client (client_secret not provided):
            - Uses token_endpoint_auth_method="none"
            - PKCE is the sole authentication mechanism
            - Salesforce: "Require Secret for Web Server Flow" disabled

    Environment variables:
        SALESFORCE_CLIENT_ID: Salesforce Connected App client ID (required)
        SALESFORCE_CLIENT_SECRET: Salesforce Connected App client secret (optional)
        SALESFORCE_LOGIN_URL: Login URL (default: https://login.salesforce.com)
        BASE_URL: Public URL of this server (default: http://localhost:8000)
        OAUTH_REDIRECT_PATH: OAuth callback path (default: /auth/callback)
        OAUTH_REQUIRED_SCOPES: Comma-separated scopes (default: api,refresh_token)

    Example:
        >>> # Confidential client (with client_secret)
        >>> proxy = SalesforceOAuthProxy(client_id="...", client_secret="...")

        >>> # PKCE-only public client (no client_secret)
        >>> proxy = SalesforceOAuthProxy(client_id="...")

        >>> mcp = FastMCP("Salesforce MCP", auth=proxy.oauth_proxy)
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str | None = None,
        login_url: str = "https://login.salesforce.com",
        base_url: str = "http://localhost:8000",
        redirect_path: str = "/auth/callback",
        required_scopes: list[str] | None = None,
        storage: "AsyncKeyValue | None" = None,
    ) -> None:
        """Initialize the Salesforce OAuth Proxy.

        Args:
            client_id: Salesforce Connected App client ID
            client_secret: Connected App client secret (optional for PKCE-only)
            login_url: Salesforce login URL (login or test.salesforce.com)
            base_url: Public URL of this MCP server
            redirect_path: OAuth callback redirect path (default: /auth/callback)
            required_scopes: OAuth scopes required for access
            storage: Optional storage backend for tokens/clients
        """
        self.client_id = client_id
        # Store empty string for PKCE-only mode (FastMCP requires string)
        self.client_secret = client_secret or ""
        self.login_url = login_url.rstrip("/")
        self.base_url = base_url.rstrip("/")
        self.redirect_path = redirect_path
        self.required_scopes = required_scopes or ["api", "refresh_token"]

        # Determine if using PKCE-only mode
        self._is_pkce_only = not client_secret

        # Token endpoint auth method:
        # - "client_secret_post": Confidential client (client_secret in body)
        # - "none": Public client (PKCE-only, no client_secret)
        self._token_auth_method = "none" if self._is_pkce_only else "client_secret_post"

        # Salesforce OAuth endpoints
        self.authorization_endpoint = f"{self.login_url}/services/oauth2/authorize"
        self.token_endpoint = f"{self.login_url}/services/oauth2/token"
        self.revocation_endpoint = f"{self.login_url}/services/oauth2/revoke"

        # Create token verifier (validates Salesforce access tokens)
        self._token_verifier = SalesforceTokenVerifier()

        # Create storage backend
        self._storage = storage or create_storage()

        # Create FastMCP OAuthProxy
        self._oauth_proxy = self._create_oauth_proxy()

        logger.info(
            "SalesforceOAuthProxy initialized: login_url=%s, base_url=%s, pkce_only=%s",
            self.login_url,
            self.base_url,
            self._is_pkce_only,
        )

    def _create_oauth_proxy(self) -> OAuthProxy:
        """Create the FastMCP OAuthProxy instance.

        Configures the proxy based on the authentication mode:
        - Confidential client: Uses client_secret_post authentication
        - PKCE-only: Uses token_endpoint_auth_method="none"
        """
        return OAuthProxy(
            # Upstream Salesforce OAuth endpoints
            upstream_authorization_endpoint=self.authorization_endpoint,
            upstream_token_endpoint=self.token_endpoint,
            upstream_revocation_endpoint=self.revocation_endpoint,
            # Salesforce Connected App credentials
            upstream_client_id=self.client_id,
            upstream_client_secret=self.client_secret,  # Empty string for PKCE-only
            # Token verification
            token_verifier=self._token_verifier,
            # Server configuration
            base_url=self.base_url,
            redirect_path=self.redirect_path,
            # Client redirect URI validation
            # Allow localhost for development and vscode/cursor for IDE integrations
            allowed_client_redirect_uris=[
                "http://localhost:*",
                "http://127.0.0.1:*",
                "vscode-webview://*",
                "cursor://*",
            ],
            # Advertised scopes
            valid_scopes=self.required_scopes,
            # Forward PKCE to Salesforce (always required)
            forward_pkce=True,
            # Require user consent before redirecting
            require_authorization_consent=True,
            # Token endpoint auth method:
            # - "client_secret_post" for confidential clients
            # - "none" for PKCE-only public clients
            token_endpoint_auth_method=self._token_auth_method,
            # Storage backend
            client_storage=self._storage,
        )

    @property
    def oauth_proxy(self) -> OAuthProxy:
        """Get the FastMCP OAuthProxy instance.

        This is the auth provider to pass to FastMCP:
            mcp = FastMCP("name", auth=proxy.oauth_proxy)
        """
        return self._oauth_proxy

    @property
    def token_verifier(self) -> SalesforceTokenVerifier:
        """Get the token verifier instance."""
        return self._token_verifier

    @property
    def is_pkce_only(self) -> bool:
        """Return True if using PKCE-only mode (no client_secret)."""
        return self._is_pkce_only

    @classmethod
    def from_env(cls) -> "SalesforceOAuthProxy | None":
        """Create a SalesforceOAuthProxy from environment variables.

        Required environment variables:
            SALESFORCE_CLIENT_ID: Connected App client ID

        Optional environment variables:
            SALESFORCE_CLIENT_SECRET: Connected App client secret (confidential mode)
            SALESFORCE_LOGIN_URL: Login URL (default: https://login.salesforce.com)
            BASE_URL: Public URL of this server (default: http://localhost:8000)
            OAUTH_REDIRECT_PATH: OAuth callback path (default: /auth/callback)
            OAUTH_REQUIRED_SCOPES: Comma-separated scopes (default: api,refresh_token)

        Mode detection:
            - If SALESFORCE_CLIENT_SECRET is set: Confidential client mode
            - If SALESFORCE_CLIENT_SECRET is empty/unset: PKCE-only mode

        Returns:
            SalesforceOAuthProxy if client_id is configured, None otherwise
        """
        client_id = os.getenv("SALESFORCE_CLIENT_ID")
        client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")  # Optional for PKCE-only

        if not client_id:
            logger.debug("OAuth proxy not configured: SALESFORCE_CLIENT_ID not set")
            return None

        login_url = os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        redirect_path = os.getenv("OAUTH_REDIRECT_PATH", "/auth/callback")

        # Parse required scopes
        scopes_str = os.getenv("OAUTH_REQUIRED_SCOPES", "api,refresh_token")
        required_scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]

        mode = "PKCE-only" if not client_secret else "confidential"
        logger.info(
            "Creating OAuth proxy from environment: login_url=%s, base_url=%s, mode=%s",
            login_url,
            base_url,
            mode,
        )

        return cls(
            client_id=client_id,
            client_secret=client_secret,  # None for PKCE-only mode
            login_url=login_url,
            base_url=base_url,
            redirect_path=redirect_path,
            required_scopes=required_scopes,
        )

    async def close(self) -> None:
        """Clean up resources."""
        await self._token_verifier.close()
