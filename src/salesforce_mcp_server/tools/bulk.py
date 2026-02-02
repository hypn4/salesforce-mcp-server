"""Bulk API tools for Salesforce MCP."""

from typing import Any

from fastmcp import FastMCP

from ..helpers import get_operations
from ..logging_config import get_logger

logger = get_logger("tools.bulk")


def register_bulk_tools(mcp: FastMCP) -> None:
    """Register bulk operation tools with the MCP server."""

    @mcp.tool()
    async def salesforce_bulk_query(
        sobject: str,
        soql: str,
    ) -> list[dict[str, Any]]:
        """Execute a bulk query for large data sets.

        Use this for queries that may return more than 2,000 records.
        The Bulk API is optimized for large data volumes and runs asynchronously.

        Args:
            sobject: SObject type being queried (e.g., 'Account', 'Contact')
            soql: SOQL query string

        Returns:
            List of all matching records
        """
        ops = await get_operations()
        return ops.bulk_query(sobject, soql)

    @mcp.tool()
    async def salesforce_bulk_insert(
        sobject: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Bulk insert multiple records.

        Use this to create many records efficiently. The Bulk API
        processes records in batches and is optimized for high volumes.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact', 'Lead')
            records: List of records to insert.
                     Each record is a dict of field name to value.
                     Example: [{"Name": "Acme"}, {"Name": "Globex"}]

        Returns:
            List of results for each record, containing:
            - success: Whether the insert succeeded
            - id: The new record ID (if successful)
            - errors: Any errors that occurred
        """
        ops = await get_operations()
        return ops.bulk_insert(sobject, records)

    @mcp.tool()
    async def salesforce_bulk_update(
        sobject: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Bulk update multiple records.

        Use this to update many records efficiently.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact')
            records: List of records to update. Each record MUST include
                     an 'Id' field to identify which record to update.
                     Example: [
                         {"Id": "001xx...", "Industry": "Tech"},
                         {"Id": "001xx...", "Industry": "Finance"}
                     ]

        Returns:
            List of results for each record with success status
        """
        ops = await get_operations()
        return ops.bulk_update(sobject, records)

    @mcp.tool()
    async def salesforce_bulk_delete(
        sobject: str,
        record_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Bulk delete multiple records.

        Use this to delete many records efficiently.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact')
            record_ids: List of record IDs to delete.
                        Example: ["001xx000...", "001xx000..."]

        Returns:
            List of results for each record with success status
        """
        ops = await get_operations()
        return ops.bulk_delete(sobject, record_ids)
