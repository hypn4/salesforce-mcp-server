"""Record CRUD tools for Salesforce MCP."""

from typing import Any

from fastmcp import FastMCP

from ..helpers import get_operations
from ..logging_config import get_logger

logger = get_logger("tools.records")


def register_record_tools(mcp: FastMCP) -> None:
    """Register record CRUD tools with the MCP server."""

    @mcp.tool()
    async def salesforce_get_record(
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
        ops = await get_operations()
        return ops.get_record(sobject, record_id, fields)

    @mcp.tool()
    async def salesforce_create_record(
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
        ops = await get_operations()
        return ops.create_record(sobject, data)

    @mcp.tool()
    async def salesforce_update_record(
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
        ops = await get_operations()
        return ops.update_record(sobject, record_id, data)

    @mcp.tool()
    async def salesforce_delete_record(
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
        ops = await get_operations()
        return ops.delete_record(sobject, record_id)

    @mcp.tool()
    async def salesforce_upsert_record(
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
        ops = await get_operations()
        return ops.upsert_record(sobject, external_id_field, data)
