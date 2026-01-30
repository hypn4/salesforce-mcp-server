"""OAuth module for Salesforce MCP.

Provides token verification and access utilities for FastMCP OAuthProxy integration.
"""

from .storage import create_storage
from .token_access import TokenInfo, get_salesforce_token
from .token_verifier import SalesforceTokenVerifier

__all__ = [
    "SalesforceTokenVerifier",
    "TokenInfo",
    "create_storage",
    "get_salesforce_token",
]
