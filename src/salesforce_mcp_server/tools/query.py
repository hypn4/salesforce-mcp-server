"""SOQL/SOSL query tools for Salesforce MCP."""

from typing import Any

from fastmcp import Context, FastMCP

from ..errors import AuthenticationError
from ..logging_config import get_logger
from ..oauth.token_access import get_salesforce_token
from ..salesforce.client_manager import SalesforceClientManager
from ..salesforce.operations import SalesforceOperations

logger = get_logger("tools.query")


def register_query_tools(mcp: FastMCP) -> None:
    """Register query-related tools with the MCP server."""

    @mcp.tool()
    async def salesforce_query(
        ctx: Context,
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
        app_ctx = ctx.request_context.lifespan_context
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_query called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info("salesforce_query: user_id=%s", token_info.user_id)
        logger.debug("SOQL: %s", soql[:200])
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.query(soql, include_deleted=include_deleted)

    @mcp.tool()
    async def salesforce_query_all(
        ctx: Context,
        soql: str,
    ) -> dict[str, Any]:
        """Execute a SOQL query including deleted and archived records.

        This is equivalent to calling salesforce_query with include_deleted=True.

        Args:
            soql: SOQL query string

        Returns:
            Query results including deleted/archived records
        """
        app_ctx = ctx.request_context.lifespan_context
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_query_all called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info("salesforce_query_all: user_id=%s", token_info.user_id)
        logger.debug("SOQL: %s", soql[:200])
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.query(soql, include_deleted=True)

    @mcp.tool()
    async def salesforce_query_more(
        ctx: Context,
        next_records_url: str,
    ) -> dict[str, Any]:
        """Fetch additional records from a previous query.

        Use this when a query returns done=False and provides a nextRecordsUrl.

        Args:
            next_records_url: The nextRecordsUrl from a previous query response

        Returns:
            Additional query results
        """
        app_ctx = ctx.request_context.lifespan_context
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_query_more called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info("salesforce_query_more: user_id=%s", token_info.user_id)
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.query_more(next_records_url)

    @mcp.tool()
    async def salesforce_search(
        ctx: Context,
        sosl: str,
    ) -> list[dict[str, Any]]:
        """Execute a SOSL full-text search.

        Args:
            sosl: SOSL search string
                  (e.g., "FIND {Acme} IN ALL FIELDS RETURNING Account(Id, Name)")

        Returns:
            List of matching records grouped by object type
        """
        app_ctx = ctx.request_context.lifespan_context
        client_manager: SalesforceClientManager = app_ctx.client_manager

        token_info = get_salesforce_token()
        if token_info is None:
            logger.error("salesforce_search called without authentication")
            raise AuthenticationError(
                "Authentication required. Please authenticate with Salesforce first."
            )

        logger.info("salesforce_search: user_id=%s", token_info.user_id)
        logger.debug("SOSL: %s", sosl[:200])
        client = await client_manager.get_client(token_info)
        ops = SalesforceOperations(client)
        return ops.search(sosl)
