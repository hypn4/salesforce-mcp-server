"""Unified helpers for Salesforce operations.

This module provides high-level helper functions that encapsulate all the
boilerplate needed to get an authenticated SalesforceOperations instance.

Usage:
    from .helpers import get_operations

    @mcp.tool()
    async def salesforce_query(soql: str) -> dict[str, Any]:
        ops = await get_operations()
        return ops.query(soql)
"""

from __future__ import annotations

from .context import get_client_manager
from .errors import AuthenticationError
from .logging_config import get_logger
from .oauth.token_access import TokenInfo, get_salesforce_token
from .salesforce.operations import SalesforceOperations

logger = get_logger("helpers")


async def get_operations() -> SalesforceOperations:
    """Get an authenticated SalesforceOperations instance.

    This function encapsulates all the boilerplate needed in every tool:
    1. Token validation
    2. Authentication check
    3. Client retrieval
    4. Operations wrapper creation

    Returns:
        SalesforceOperations instance ready to use

    Raises:
        AuthenticationError: If no valid authentication is available
        RuntimeError: If client manager is not initialized
    """
    token_info = get_salesforce_token()
    if token_info is None:
        logger.error("Operation called without authentication")
        raise AuthenticationError(
            "Authentication required. Please authenticate with Salesforce first."
        )

    logger.debug("Getting operations for user_id=%s", token_info.user_id)
    client_manager = get_client_manager()
    client = await client_manager.get_client(token_info)
    return SalesforceOperations(client)


def get_token() -> TokenInfo:
    """Get the current authentication token.

    Use this when you need access to token info (e.g., for logging user_id).

    Returns:
        TokenInfo with user credentials

    Raises:
        AuthenticationError: If no valid authentication is available
    """
    token_info = get_salesforce_token()
    if token_info is None:
        raise AuthenticationError(
            "Authentication required. Please authenticate with Salesforce first."
        )
    return token_info
