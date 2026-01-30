"""Core Salesforce operations using simple-salesforce."""

from typing import Any

from simple_salesforce.api import Salesforce

from ..errors import (
    ValidationError,
    handle_salesforce_errors,
)
from ..logging_config import get_logger

logger = get_logger("salesforce.operations")


class SalesforceOperations:
    """Provides core Salesforce operations wrapping simple-salesforce."""

    def __init__(self, client: Salesforce) -> None:
        self._client = client

    @handle_salesforce_errors
    def query(self, soql: str, include_deleted: bool = False) -> dict[str, Any]:
        """Execute a SOQL query.

        Args:
            soql: SOQL query string
            include_deleted: Include deleted/archived records

        Returns:
            Query results with records and metadata
        """
        logger.debug("Executing SOQL query: %s", soql[:200])
        if include_deleted:
            result = self._client.query_all(soql)
        else:
            result = self._client.query(soql)
        result_dict = dict(result)
        record_count = result_dict.get("totalSize", 0)
        logger.info("Query completed: %d records returned", record_count)
        if record_count > 2000:
            logger.warning("Large result set: %d records", record_count)
        return result_dict

    @handle_salesforce_errors
    def query_more(
        self,
        next_records_url: str,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Fetch more records from a previous query.

        Args:
            next_records_url: URL from previous query response
            include_deleted: Include deleted/archived records

        Returns:
            Additional query results
        """
        logger.debug("Fetching more records from: %s", next_records_url)
        result = self._client.query_more(
            next_records_url,
            identifier_is_url=True,
        )
        result_dict = dict(result)
        record_count = len(result_dict.get("records", []))
        logger.info("Query more completed: %d additional records", record_count)
        return result_dict

    @handle_salesforce_errors
    def search(self, sosl: str) -> list[dict[str, Any]]:
        """Execute a SOSL search.

        Args:
            sosl: SOSL search string

        Returns:
            Search results
        """
        logger.debug("Executing SOSL search: %s", sosl[:200])
        result = self._client.search(sosl)
        records = result.get("searchRecords", [])
        logger.info("Search completed: %d records found", len(records))
        return records

    @handle_salesforce_errors
    def get_record(
        self,
        sobject: str,
        record_id: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single record by ID.

        Args:
            sobject: SObject type (e.g., 'Account', 'Contact')
            record_id: Salesforce record ID
            fields: Optional list of fields to retrieve

        Returns:
            Record data
        """
        logger.debug("Getting %s record: %s", sobject, record_id)
        sf_object = getattr(self._client, sobject)
        if fields:
            result = sf_object.get(record_id, fields=fields)
        else:
            result = sf_object.get(record_id)
        logger.info("Retrieved %s record: %s", sobject, record_id)
        return dict(result)

    @handle_salesforce_errors
    def create_record(
        self,
        sobject: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new record.

        Args:
            sobject: SObject type
            data: Record field values

        Returns:
            Created record info with ID
        """
        if not data:
            raise ValidationError("Record data cannot be empty")

        logger.debug("Creating %s record", sobject)
        sf_object = getattr(self._client, sobject)
        result = sf_object.create(data)
        result_dict = dict(result)
        logger.info("Created %s record: %s", sobject, result_dict.get("id"))
        return result_dict

    @handle_salesforce_errors
    def update_record(
        self,
        sobject: str,
        record_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing record.

        Args:
            sobject: SObject type
            record_id: Salesforce record ID
            data: Fields to update

        Returns:
            Update result
        """
        if not data:
            raise ValidationError("Update data cannot be empty")

        logger.debug("Updating %s record: %s", sobject, record_id)
        sf_object = getattr(self._client, sobject)
        result = sf_object.update(record_id, data)
        logger.info("Updated %s record: %s", sobject, record_id)
        return {"success": True, "id": record_id, "result": result}

    @handle_salesforce_errors
    def delete_record(
        self,
        sobject: str,
        record_id: str,
    ) -> dict[str, Any]:
        """Delete a record.

        Args:
            sobject: SObject type
            record_id: Salesforce record ID

        Returns:
            Deletion result
        """
        logger.debug("Deleting %s record: %s", sobject, record_id)
        sf_object = getattr(self._client, sobject)
        result = sf_object.delete(record_id)
        logger.info("Deleted %s record: %s", sobject, record_id)
        return {"success": True, "id": record_id, "result": result}

    @handle_salesforce_errors
    def describe_object(self, sobject: str) -> dict[str, Any]:
        """Get metadata for an SObject.

        Args:
            sobject: SObject type

        Returns:
            SObject metadata including fields, relationships, etc.
        """
        logger.debug("Describing object: %s", sobject)
        sf_object = getattr(self._client, sobject)
        result = sf_object.describe()
        logger.info("Described object: %s", sobject)
        return dict(result)

    @handle_salesforce_errors
    def list_objects(self) -> list[dict[str, Any]]:
        """List all available SObjects.

        Returns:
            List of SObject descriptions
        """
        logger.debug("Listing all objects")
        result = self._client.describe()
        if result is None:
            return []
        objects = result.get("sobjects", [])
        logger.info("Listed %d objects", len(objects))
        return objects

    @handle_salesforce_errors
    def bulk_query(self, sobject: str, soql: str) -> list[dict[str, Any]]:
        """Execute a bulk query.

        Args:
            sobject: SObject type for the query
            soql: SOQL query string

        Returns:
            Query results as a list of records
        """
        logger.debug("Executing bulk query on %s: %s", sobject, soql[:200])
        bulk_handler = getattr(self._client.bulk, sobject)
        result = bulk_handler.query(soql)
        result_list = list(result)
        logger.info("Bulk query completed: %d records", len(result_list))
        if len(result_list) > 10000:
            logger.warning("Large bulk query result: %d records", len(result_list))
        return result_list

    @handle_salesforce_errors
    def bulk_insert(
        self,
        sobject: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Bulk insert records.

        Args:
            sobject: SObject type
            records: List of records to insert

        Returns:
            Insert results for each record
        """
        if not records:
            raise ValidationError("Records list cannot be empty")

        logger.debug("Bulk inserting %d %s records", len(records), sobject)
        bulk_handler = getattr(self._client.bulk, sobject)
        result = bulk_handler.insert(records)  # type: ignore[arg-type]
        result_list = list(result)
        success_count = sum(1 for r in result_list if r.get("success"))
        total = len(result_list)
        logger.info("Bulk insert completed: %d/%d successful", success_count, total)
        if success_count < total:
            failed = total - success_count
            logger.warning("Bulk insert partial failure: %d/%d failed", failed, total)
        return result_list

    @handle_salesforce_errors
    def bulk_update(
        self,
        sobject: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Bulk update records.

        Args:
            sobject: SObject type
            records: List of records to update (must include Id field)

        Returns:
            Update results for each record
        """
        if not records:
            raise ValidationError("Records list cannot be empty")

        for record in records:
            if "Id" not in record:
                raise ValidationError("Each record must include an 'Id' field")

        logger.debug("Bulk updating %d %s records", len(records), sobject)
        bulk_handler = getattr(self._client.bulk, sobject)
        result = bulk_handler.update(records)  # type: ignore[arg-type]
        result_list = list(result)
        success_count = sum(1 for r in result_list if r.get("success"))
        total = len(result_list)
        logger.info("Bulk update completed: %d/%d successful", success_count, total)
        if success_count < total:
            failed = total - success_count
            logger.warning("Bulk update partial failure: %d/%d failed", failed, total)
        return result_list

    @handle_salesforce_errors
    def bulk_delete(
        self,
        sobject: str,
        record_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Bulk delete records.

        Args:
            sobject: SObject type
            record_ids: List of record IDs to delete

        Returns:
            Delete results for each record
        """
        if not record_ids:
            raise ValidationError("Record IDs list cannot be empty")

        logger.debug("Bulk deleting %d %s records", len(record_ids), sobject)
        delete_records = [{"Id": rid} for rid in record_ids]
        bulk_handler = getattr(self._client.bulk, sobject)
        result = bulk_handler.delete(delete_records)  # type: ignore[arg-type]
        result_list = list(result)
        success_count = sum(1 for r in result_list if r.get("success"))
        total = len(result_list)
        logger.info("Bulk delete completed: %d/%d successful", success_count, total)
        if success_count < total:
            failed = total - success_count
            logger.warning("Bulk delete partial failure: %d/%d failed", failed, total)
        return result_list

    @handle_salesforce_errors
    def upsert_record(
        self,
        sobject: str,
        external_id_field: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Upsert a record using an external ID.

        Args:
            sobject: SObject type
            external_id_field: Name of the external ID field
            data: Record data including the external ID value

        Returns:
            Upsert result
        """
        if not data:
            raise ValidationError("Record data cannot be empty")

        if external_id_field not in data:
            raise ValidationError(
                f"Data must include the external ID field: {external_id_field}"
            )

        logger.debug("Upserting %s record with %s", sobject, external_id_field)
        sf_object = getattr(self._client, sobject)
        external_id_value = data[external_id_field]
        result = sf_object.upsert(f"{external_id_field}/{external_id_value}", data)
        logger.info(
            "Upserted %s record with %s=%s",
            sobject,
            external_id_field,
            external_id_value,
        )
        return {"success": True, "result": result}
