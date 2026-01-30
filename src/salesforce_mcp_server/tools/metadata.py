"""Metadata tools for Salesforce MCP."""

from typing import Any

from fastmcp import Context, FastMCP

from ..errors import AuthenticationError
from ..logging_config import get_logger
from ..oauth.token_access import get_salesforce_token
from ..salesforce.client_manager import SalesforceClientManager
from ..salesforce.operations import SalesforceOperations

logger = get_logger("tools.metadata")


def register_metadata_tools(mcp: FastMCP) -> None:
    """Register metadata tools with the MCP server."""

    @mcp.tool()
    async def salesforce_describe_object(
        ctx: Context,
        sobject: str,
    ) -> dict[str, Any]:
        """Get metadata for a Salesforce SObject.

        Returns detailed information about an object including its fields,
        relationships, record types, and other metadata.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact', 'Lead', 'Opportunity')

        Returns:
            Object metadata including:
            - name: API name of the object
            - label: Display name
            - fields: List of field definitions with type, length, required, etc.
            - childRelationships: Related objects
            - recordTypeInfos: Available record types
            - keyPrefix: Object ID prefix
            - And more...
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_describe_object called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info(
            "salesforce_describe_object called: user_id=%s, sobject=%s",
            token_info.user_id,
            sobject,
        )
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.describe_object(sobject)

    @mcp.tool()
    async def salesforce_list_objects(
        ctx: Context,
    ) -> list[dict[str, Any]]:
        """List all available SObjects in the Salesforce org.

        Returns a list of all objects accessible to the current user,
        including standard objects (Account, Contact, etc.) and custom objects.

        Returns:
            List of object summaries, each containing:
            - name: API name
            - label: Display name
            - keyPrefix: Object ID prefix
            - custom: Whether it's a custom object
            - queryable: Whether SOQL queries are supported
            - createable: Whether records can be created
            - updateable: Whether records can be updated
            - deletable: Whether records can be deleted
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_list_objects called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info("salesforce_list_objects called: user_id=%s", token_info.user_id)
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.list_objects()

    @mcp.tool()
    async def salesforce_get_object_fields(
        ctx: Context,
        sobject: str,
    ) -> list[dict[str, Any]]:
        """Get field information for a Salesforce SObject.

        This is a convenience method that returns just the fields array
        from the describe call, which is often what's needed.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact')

        Returns:
            List of field definitions, each containing:
            - name: API name of the field
            - label: Display name
            - type: Field type (string, picklist, reference, etc.)
            - length: Maximum length for text fields
            - nillable: Whether the field can be null
            - createable: Whether the field can be set on create
            - updateable: Whether the field can be updated
            - picklistValues: For picklist fields, available values
            - referenceTo: For reference fields, related object(s)
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_get_object_fields called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info(
            "salesforce_get_object_fields called: user_id=%s, sobject=%s",
            token_info.user_id,
            sobject,
        )
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        metadata = ops.describe_object(sobject)
        return metadata.get("fields", [])
