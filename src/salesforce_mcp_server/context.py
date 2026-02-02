"""Module-level context management for application-wide singletons.

This module provides a decoupled way to access the SalesforceClientManager
from anywhere in the codebase without passing it through function parameters.

Note: We use a simple module-level variable instead of ContextVar because
client_manager is an application-wide singleton, not request-scoped data.
ContextVar would isolate the value per-async-context, making it invisible
to HTTP request handlers.

Usage:
    # In server.py lifespan:
    from .context import set_client_manager
    set_client_manager(client_manager)

    # In tools or helpers:
    from .context import get_client_manager
    manager = get_client_manager()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .salesforce.client_manager import SalesforceClientManager

_client_manager: "SalesforceClientManager | None" = None


def set_client_manager(manager: "SalesforceClientManager") -> None:
    """Set the client manager for global access.

    Called during server lifespan initialization to make the client manager
    available to all tools.

    Args:
        manager: The SalesforceClientManager instance to store
    """
    global _client_manager
    _client_manager = manager


def get_client_manager() -> "SalesforceClientManager":
    """Get the client manager.

    Returns:
        The SalesforceClientManager instance

    Raises:
        RuntimeError: If client manager has not been initialized
    """
    if _client_manager is None:
        raise RuntimeError("Client manager not initialized")
    return _client_manager
