"""Token access utilities for MCP tools.

Provides helper functions to extract Salesforce token information
from FastMCP context for use in tool handlers.
"""

from __future__ import annotations

import os

import msgspec

from ..logging_config import get_logger

logger = get_logger("oauth.token_access")


class TokenInfo(msgspec.Struct, kw_only=True):
    """Information extracted from a validated Salesforce token."""

    user_id: str
    org_id: str
    username: str
    instance_url: str
    access_token: str


def get_salesforce_token() -> TokenInfo | None:
    """Get the current Salesforce token from FastMCP context.

    This function extracts token information from FastMCP's OAuth context,
    which is populated by SalesforceTokenVerifier after OAuthProxy validates
    the incoming request.

    Priority:
    1. FastMCP get_access_token() - OAuth-authenticated requests
    2. Environment variables - fallback for development/testing

    Returns:
        TokenInfo if authentication is available, None otherwise
    """
    # 1. Try FastMCP OAuth context (primary path for HTTP mode)
    try:
        from fastmcp.server.dependencies import get_access_token

        access_token = get_access_token()
        if access_token is not None:
            # Use sf_access_token from claims (set by SalesforceTokenVerifier)
            sf_token = access_token.claims.get("sf_access_token", access_token.token)

            token_info = TokenInfo(
                user_id=access_token.claims.get("user_id", ""),
                org_id=access_token.claims.get("org_id", ""),
                username=access_token.claims.get("username", ""),
                instance_url=access_token.claims.get("instance_url", ""),
                access_token=sf_token,
            )
            logger.debug("Got token from FastMCP: user_id=%s", token_info.user_id)
            return token_info
    except (ImportError, LookupError):
        logger.debug("FastMCP get_access_token not available")

    # 2. Fallback to environment variables (for development/testing)
    access_token_env = os.getenv("SALESFORCE_ACCESS_TOKEN")
    instance_url_env = os.getenv("SALESFORCE_INSTANCE_URL")

    if access_token_env and instance_url_env:
        token_info = TokenInfo(
            user_id=os.getenv("SALESFORCE_USER_ID", "env_user"),
            org_id=os.getenv("SALESFORCE_ORG_ID", "env_org"),
            username=os.getenv("SALESFORCE_USERNAME", "env_user"),
            instance_url=instance_url_env,
            access_token=access_token_env,
        )
        logger.debug("Got token from environment: user_id=%s", token_info.user_id)
        return token_info

    logger.debug("No token available")
    return None
