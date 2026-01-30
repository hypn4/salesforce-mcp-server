"""Custom exceptions for Salesforce MCP Server."""

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from simple_salesforce.exceptions import (
    SalesforceAuthenticationFailed,
    SalesforceExpiredSession,
    SalesforceGeneralError,
    SalesforceMalformedRequest,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
)

from .logging_config import get_logger

logger = get_logger("errors")

P = ParamSpec("P")
R = TypeVar("R")


class SalesforceMCPError(Exception):
    """Base exception for Salesforce MCP errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(SalesforceMCPError):
    """Authentication-related errors."""


class SessionExpiredError(AuthenticationError):
    """Session has expired and needs refresh."""


class SalesforceAPIError(SalesforceMCPError):
    """Errors from Salesforce API calls."""


class RateLimitError(SalesforceAPIError):
    """Rate limit exceeded."""


class ResourceNotFoundError(SalesforceAPIError):
    """Requested resource not found."""


class ValidationError(SalesforceMCPError):
    """Input validation errors."""


def handle_salesforce_errors(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator to convert simple-salesforce exceptions to MCP-friendly errors."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except SalesforceExpiredSession as e:
            logger.error("Session expired: %s", e)
            raise SessionExpiredError(
                "Salesforce session has expired. Please re-authenticate.",
                {"original_error": str(e)},
            ) from e
        except SalesforceAuthenticationFailed as e:
            logger.error("Authentication failed: %s", e)
            raise AuthenticationError(
                "Salesforce authentication failed. Please check your credentials.",
                {"original_error": str(e)},
            ) from e
        except SalesforceResourceNotFound as e:
            logger.error("Resource not found: %s", e)
            raise ResourceNotFoundError(
                "The requested Salesforce resource was not found.",
                {"original_error": str(e)},
            ) from e
        except SalesforceRefusedRequest as e:
            error_msg = str(e)
            if "REQUEST_LIMIT_EXCEEDED" in error_msg:
                logger.error("Rate limit exceeded: %s", error_msg)
                raise RateLimitError(
                    "Salesforce API rate limit exceeded. Please try again later.",
                    {"original_error": error_msg},
                ) from e
            logger.error("Request refused: %s", error_msg)
            raise SalesforceAPIError(
                f"Salesforce refused the request: {error_msg}",
                {"original_error": error_msg},
            ) from e
        except SalesforceMalformedRequest as e:
            logger.error("Malformed request: %s", e)
            raise ValidationError(
                f"Malformed request to Salesforce: {e}",
                {"original_error": str(e)},
            ) from e
        except SalesforceGeneralError as e:
            logger.error("Salesforce API error: %s", e)
            raise SalesforceAPIError(
                f"Salesforce API error: {e}",
                {"original_error": str(e)},
            ) from e

    return wrapper


async def handle_salesforce_errors_async(
    func: Callable[P, R],
) -> Callable[P, R]:
    """Async version of handle_salesforce_errors decorator."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except SalesforceExpiredSession as e:
            logger.error("Session expired: %s", e)
            raise SessionExpiredError(
                "Salesforce session has expired. Please re-authenticate.",
                {"original_error": str(e)},
            ) from e
        except SalesforceAuthenticationFailed as e:
            logger.error("Authentication failed: %s", e)
            raise AuthenticationError(
                "Salesforce authentication failed. Please check your credentials.",
                {"original_error": str(e)},
            ) from e
        except SalesforceResourceNotFound as e:
            logger.error("Resource not found: %s", e)
            raise ResourceNotFoundError(
                "The requested Salesforce resource was not found.",
                {"original_error": str(e)},
            ) from e
        except SalesforceRefusedRequest as e:
            error_msg = str(e)
            if "REQUEST_LIMIT_EXCEEDED" in error_msg:
                logger.error("Rate limit exceeded: %s", error_msg)
                raise RateLimitError(
                    "Salesforce API rate limit exceeded. Please try again later.",
                    {"original_error": error_msg},
                ) from e
            logger.error("Request refused: %s", error_msg)
            raise SalesforceAPIError(
                f"Salesforce refused the request: {error_msg}",
                {"original_error": error_msg},
            ) from e
        except SalesforceMalformedRequest as e:
            logger.error("Malformed request: %s", e)
            raise ValidationError(
                f"Malformed request to Salesforce: {e}",
                {"original_error": str(e)},
            ) from e
        except SalesforceGeneralError as e:
            logger.error("Salesforce API error: %s", e)
            raise SalesforceAPIError(
                f"Salesforce API error: {e}",
                {"original_error": str(e)},
            ) from e

    return wrapper
