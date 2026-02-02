"""SOQL/SOSL query tools for Salesforce MCP."""

from typing import Any

from fastmcp import FastMCP

from ..helpers import get_operations
from ..logging_config import get_logger

logger = get_logger("tools.query")


def register_query_tools(mcp: FastMCP) -> None:
    """Register query-related tools with the MCP server."""

    @mcp.tool()
    async def salesforce_query(
        soql: str,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Execute a SOQL query against Salesforce.

        Args:
            soql: SOQL query string (e.g., "SELECT Id, Name FROM Account LIMIT 10")
            include_deleted: Include deleted and archived records (default: False)

        Returns:
            Query results including:
            - totalSize: Total number of records matching the query
            - done: Whether all records have been returned
            - records: List of matching records
            - nextRecordsUrl: URL to fetch more records (if done is False)
        """
        ops = await get_operations()
        return ops.query(soql, include_deleted=include_deleted)

    @mcp.tool()
    async def salesforce_query_all(
        soql: str,
    ) -> dict[str, Any]:
        """Execute a SOQL query including deleted and archived records.

        This is equivalent to calling salesforce_query with include_deleted=True.

        Args:
            soql: SOQL query string

        Returns:
            Query results including deleted/archived records
        """
        ops = await get_operations()
        return ops.query(soql, include_deleted=True)

    @mcp.tool()
    async def salesforce_query_more(
        next_records_url: str,
    ) -> dict[str, Any]:
        """Fetch additional records from a previous query.

        Use this when a query returns done=False and provides a nextRecordsUrl.

        Args:
            next_records_url: The nextRecordsUrl from a previous query response

        Returns:
            Additional query results
        """
        ops = await get_operations()
        return ops.query_more(next_records_url)

    @mcp.tool()
    async def salesforce_search(
        sosl: str,
    ) -> list[dict[str, Any]]:
        """Execute a SOSL full-text search.

        Args:
            sosl: SOSL search string
                  (e.g., "FIND {Acme} IN ALL FIELDS RETURNING Account(Id, Name)")

        Returns:
            List of matching records grouped by object type
        """
        ops = await get_operations()
        return ops.search(sosl)
