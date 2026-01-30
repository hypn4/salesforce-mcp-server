"""Record CRUD tools for Salesforce MCP."""

from typing import Any

from fastmcp import Context, FastMCP

from ..errors import AuthenticationError
from ..logging_config import get_logger
from ..oauth.token_access import get_salesforce_token
from ..salesforce.client_manager import SalesforceClientManager
from ..salesforce.operations import SalesforceOperations

logger = get_logger("tools.records")


def register_record_tools(mcp: FastMCP) -> None:
    """Register record CRUD tools with the MCP server."""

    @mcp.tool()
    async def salesforce_get_record(
        ctx: Context,
        sobject: str,
        record_id: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single Salesforce record by ID.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact', 'Lead')
            record_id: Salesforce record ID (18-character ID)
            fields: Optional list of specific fields to retrieve.
                    If not provided, returns all accessible fields.

        Returns:
            Record data with requested fields
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_get_record called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info(
            "salesforce_get_record called: user_id=%s, sobject=%s, record_id=%s",
            token_info.user_id,
            sobject,
            record_id,
        )
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.get_record(sobject, record_id, fields)

    @mcp.tool()
    async def salesforce_create_record(
        ctx: Context,
        sobject: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new Salesforce record.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact', 'Lead')
            data: Record field values as key-value pairs.
                  Example: {"Name": "Acme Corp", "Industry": "Technology"}

        Returns:
            Created record info including:
            - id: The new record's ID
            - success: Whether creation succeeded
            - errors: Any errors that occurred
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_create_record called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info(
            "salesforce_create_record called: user_id=%s, sobject=%s",
            token_info.user_id,
            sobject,
        )
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.create_record(sobject, data)

    @mcp.tool()
    async def salesforce_update_record(
        ctx: Context,
        sobject: str,
        record_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing Salesforce record.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact', 'Lead')
            record_id: Salesforce record ID (18-character ID)
            data: Fields to update as key-value pairs.
                  Example: {"Industry": "Finance", "Website": "https://acme.com"}

        Returns:
            Update result with success status
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_update_record called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info(
            "salesforce_update_record called: user_id=%s, sobject=%s, record_id=%s",
            token_info.user_id,
            sobject,
            record_id,
        )
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.update_record(sobject, record_id, data)

    @mcp.tool()
    async def salesforce_delete_record(
        ctx: Context,
        sobject: str,
        record_id: str,
    ) -> dict[str, Any]:
        """Delete a Salesforce record.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact', 'Lead')
            record_id: Salesforce record ID (18-character ID)

        Returns:
            Deletion result with success status
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_delete_record called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info(
            "salesforce_delete_record called: user_id=%s, sobject=%s, record_id=%s",
            token_info.user_id,
            sobject,
            record_id,
        )
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.delete_record(sobject, record_id)

    @mcp.tool()
    async def salesforce_upsert_record(
        ctx: Context,
        sobject: str,
        external_id_field: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Upsert a record using an external ID field.

        If a record with the external ID exists, it will be updated.
        Otherwise, a new record will be created.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact')
            external_id_field: Name of the external ID field
            data: Record data including the external ID field value.
                  Example: {"External_Id__c": "EXT-001", "Name": "Acme Corp"}

        Returns:
            Upsert result with success status
        """
        if ctx.request_context is None:
            raise RuntimeError("Request context not available")
        app_ctx = ctx.request_context.lifespan_context
        if app_ctx is None:
            raise RuntimeError("Application context not initialized")
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_upsert_record called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info(
            "salesforce_upsert_record: user_id=%s, sobject=%s, ext_id=%s",
            token_info.user_id,
            sobject,
            external_id_field,
        )
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.upsert_record(sobject, external_id_field, data)
