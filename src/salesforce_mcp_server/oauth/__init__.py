"""OAuth module for Salesforce MCP.

This module provides OAuth authentication support for the Salesforce MCP server:

- **Bearer Token Mode**: Clients handle OAuth themselves, server validates tokens
- **OAuth Proxy Mode**: Server acts as OAuth proxy to Salesforce

Bearer Token Mode (default):
    Clients (ADK agents, Claude Code with mcp-remote) obtain Salesforce tokens
    themselves and send them as Bearer tokens. The server validates tokens
    using the Salesforce userinfo endpoint.

OAuth Proxy Mode:
    The server implements a full OAuth 2.1 + PKCE proxy that handles
    authorization, token exchange, and session management. Clients use
    standard OAuth flows through the proxy endpoints.

Components:
    - SalesforceTokenVerifier: Validates Salesforce Bearer tokens
    - SalesforceOAuthProxy: OAuth 2.1 proxy for Salesforce Connected Apps
    - TokenInfo: Token information struct for tool handlers
    - get_salesforce_token: Helper to get token from FastMCP context
    - create_storage: Factory for OAuth token storage backends
    - PKCE utilities: generate_pkce_pair, verify_pkce, compute_challenge
"""

from .pkce import compute_challenge, generate_pkce_pair, verify_pkce
from .proxy import SalesforceOAuthProxy
from .storage import create_storage
from .token_access import TokenInfo, get_salesforce_token
from .token_verifier import SalesforceTokenVerifier

__all__ = [
    # Token verification
    "SalesforceTokenVerifier",
    # OAuth proxy
    "SalesforceOAuthProxy",
    # Token access
    "TokenInfo",
    "get_salesforce_token",
    # Storage
    "create_storage",
    # PKCE utilities
    "generate_pkce_pair",
    "verify_pkce",
    "compute_challenge",
]
