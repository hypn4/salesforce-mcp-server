"""Salesforce client management for multi-user sessions."""

import asyncio
from typing import TYPE_CHECKING

from simple_salesforce import Salesforce

from ..logging_config import get_logger

if TYPE_CHECKING:
    from ..oauth.token_access import TokenInfo

logger = get_logger("salesforce.client_manager")


class SalesforceClientManager:
    """Manages Salesforce clients for multiple users.

    Provides caching of Salesforce clients based on user_id.
    Each authenticated user gets their own client instance.
    """

    def __init__(self) -> None:
        self._clients: dict[str, Salesforce] = {}
        self._lock = asyncio.Lock()

    async def get_client(self, token_info: "TokenInfo") -> Salesforce:
        """Get a Salesforce client from token info.

        This is the primary method for tool handlers to get a client,
        using the token info from FastMCP context.

        Args:
            token_info: Verified token information from get_salesforce_token()

        Returns:
            Configured Salesforce client
        """
        async with self._lock:
            user_id = token_info.user_id

            if user_id in self._clients:
                logger.debug("Cache hit: returning client for user_id=%s", user_id)
                return self._clients[user_id]

            logger.debug("Cache miss: creating client for user_id=%s", user_id)
            client = Salesforce(
                instance_url=token_info.instance_url,
                session_id=token_info.access_token,
            )
            self._clients[user_id] = client
            logger.info("Created Salesforce client for user_id=%s", user_id)
            return client

    async def remove_client(self, user_id: str) -> None:
        """Remove a cached client.

        Args:
            user_id: The user ID to remove
        """
        async with self._lock:
            self._clients.pop(user_id, None)
            logger.debug("Removed client for user_id=%s", user_id)

    async def clear_all_clients(self) -> None:
        """Clear all cached clients."""
        async with self._lock:
            count = len(self._clients)
            self._clients.clear()
            logger.debug("Cleared %d cached clients", count)
