"""Salesforce client management module."""

from .client_manager import SalesforceClientManager
from .operations import SalesforceOperations

__all__ = [
    "SalesforceClientManager",
    "SalesforceOperations",
]
