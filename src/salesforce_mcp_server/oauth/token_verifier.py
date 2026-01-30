"""Salesforce token verification for FastMCP OAuthProxy.

This module implements the TokenVerifier protocol for FastMCP's OAuthProxy,
enabling Salesforce OAuth 2.0 PKCE authentication for MCP clients.
"""

from __future__ import annotations

import os

import httpx
import msgspec
from fastmcp.server.auth import AccessToken, TokenVerifier

from ..logging_config import get_logger

logger = get_logger("oauth.token_verifier")


class SalesforceTokenVerifier(TokenVerifier):
    """FastMCP TokenVerifier protocol implementation for Salesforce.

    This verifier implements the async verify_token interface required by
    FastMCP's OAuthProxy. It validates Salesforce access tokens by calling
    the Salesforce userinfo endpoint.

    Instance URL priority:
    1. X-Salesforce-Instance-URL HTTP header (per-request)
    2. SALESFORCE_INSTANCE_URL environment variable
    3. Default: https://login.salesforce.com
    """

    def __init__(self) -> None:
        """Initialize the verifier."""
        super().__init__()
        self._default_instance_url = os.getenv(
            "SALESFORCE_INSTANCE_URL",
            "https://login.salesforce.com",
        )
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http_client is None:
            logger.debug("Creating async HTTP client for token verification")
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def _get_instance_url(self) -> str:
        """Get instance URL from header or fallback to default.

        Returns:
            Instance URL to use for token verification
        """
        try:
            from fastmcp.server.dependencies import get_http_headers

            headers = get_http_headers()
            if headers:
                instance_url = headers.get("x-salesforce-instance-url")
                if instance_url:
                    logger.debug("Using instance URL from header: %s", instance_url)
                    return instance_url
        except (ImportError, LookupError):
            logger.debug("Could not get HTTP headers, using default instance URL")

        return self._default_instance_url

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify Salesforce token and return FastMCP AccessToken.

        This implements the FastMCP TokenVerifier protocol (async).

        Args:
            token: Salesforce access token from Authorization header

        Returns:
            AccessToken with user claims if valid, None if invalid
        """
        token_preview = token[:30] + "..." if len(token) > 30 else token
        logger.info("verify_token called: token_preview=%s", token_preview)

        instance_url = self._get_instance_url()
        client = await self._get_client()

        try:
            logger.debug("Verifying token against %s", instance_url)
            response = await client.get(
                f"{instance_url}/services/oauth2/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                logger.warning(
                    "Token verification failed: status=%d", response.status_code
                )
                return None

            data = msgspec.json.decode(response.content)

            access_token = AccessToken(
                token=token,
                client_id=data.get("user_id", ""),
                scopes=[],
                expires_at=None,
                claims={
                    "user_id": data["user_id"],
                    "org_id": data["organization_id"],
                    "username": data.get("preferred_username", data.get("sub", "")),
                    "instance_url": instance_url,
                    "sf_access_token": token,
                },
            )
            logger.info("Token verified: user_id=%s", access_token.claims["user_id"])
            return access_token

        except (httpx.HTTPError, KeyError, msgspec.DecodeError) as e:
            logger.error("Token verification error: %s", e)
            return None

    async def close(self) -> None:
        """Close the async HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
