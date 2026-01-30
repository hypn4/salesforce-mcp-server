"""Tests for the Salesforce token verifier."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from salesforce_mcp_server.oauth.token_access import TokenInfo, get_salesforce_token
from salesforce_mcp_server.oauth.token_verifier import SalesforceTokenVerifier


@pytest.fixture
def verifier():
    """Create a SalesforceTokenVerifier instance."""
    return SalesforceTokenVerifier()


@pytest.fixture
def mock_userinfo_response():
    """Mock successful userinfo response data."""
    return {
        "user_id": "005xx000001234ABC",
        "organization_id": "00Dxx0000001234ABC",
        "preferred_username": "test@example.com",
        "sub": "https://login.salesforce.com/id/00Dxx0000001234ABC/005xx000001234ABC",
    }


class TestSalesforceTokenVerifier:
    """Tests for SalesforceTokenVerifier."""

    @pytest.mark.asyncio
    async def test_verify_token_success(self, verifier, mock_userinfo_response):
        """Test successful token verification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = (
            b'{"user_id": "005xx000001234ABC", '
            b'"organization_id": "00Dxx0000001234ABC", '
            b'"preferred_username": "test@example.com"}'
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        verifier._http_client = mock_client

        result = await verifier.verify_token("test_token")

        assert result is not None
        assert result.claims["user_id"] == "005xx000001234ABC"
        assert result.claims["org_id"] == "00Dxx0000001234ABC"
        assert result.claims["username"] == "test@example.com"
        assert result.claims["sf_access_token"] == "test_token"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, verifier):
        """Test token verification with invalid token."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        verifier._http_client = mock_client

        result = await verifier.verify_token("invalid_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_network_error(self, verifier):
        """Test token verification with network error."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))

        verifier._http_client = mock_client

        result = await verifier.verify_token("test_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_close(self, verifier):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        verifier._http_client = mock_client

        await verifier.close()

        mock_client.aclose.assert_called_once()
        assert verifier._http_client is None

    def test_default_instance_url(self, verifier):
        """Test default instance URL."""
        assert verifier._default_instance_url == "https://login.salesforce.com"

    def test_custom_instance_url_from_env(self):
        """Test instance URL from environment variable."""
        with patch.dict(
            "os.environ", {"SALESFORCE_INSTANCE_URL": "https://test.salesforce.com"}
        ):
            v = SalesforceTokenVerifier()
            assert v._default_instance_url == "https://test.salesforce.com"


class TestTokenInfo:
    """Tests for TokenInfo struct."""

    def test_token_info_creation(self):
        """Test creating a TokenInfo instance."""
        token_info = TokenInfo(
            user_id="005xx000001234ABC",
            org_id="00Dxx0000001234ABC",
            username="test@example.com",
            instance_url="https://na1.salesforce.com",
            access_token="test_access_token",
        )

        assert token_info.user_id == "005xx000001234ABC"
        assert token_info.org_id == "00Dxx0000001234ABC"
        assert token_info.username == "test@example.com"
        assert token_info.instance_url == "https://na1.salesforce.com"
        assert token_info.access_token == "test_access_token"


class TestGetSalesforceToken:
    """Tests for get_salesforce_token function."""

    def test_get_token_from_env(self):
        """Test getting token from environment variables."""
        # Save original env vars
        original_access = os.environ.get("SALESFORCE_ACCESS_TOKEN")
        original_instance = os.environ.get("SALESFORCE_INSTANCE_URL")
        original_user_id = os.environ.get("SALESFORCE_USER_ID")
        original_org_id = os.environ.get("SALESFORCE_ORG_ID")
        original_username = os.environ.get("SALESFORCE_USERNAME")

        try:
            # Set test env vars
            os.environ["SALESFORCE_ACCESS_TOKEN"] = "env_access_token"
            os.environ["SALESFORCE_INSTANCE_URL"] = "https://na1.salesforce.com"
            os.environ["SALESFORCE_USER_ID"] = "env_user_id"
            os.environ["SALESFORCE_ORG_ID"] = "env_org_id"
            os.environ["SALESFORCE_USERNAME"] = "env_user@example.com"

            # Mock the fastmcp import to fail (simulates no OAuth context)
            with patch.dict("sys.modules", {"fastmcp.server.dependencies": None}):
                token_info = get_salesforce_token()

            assert token_info is not None
            assert token_info.access_token == "env_access_token"
            assert token_info.instance_url == "https://na1.salesforce.com"
            assert token_info.user_id == "env_user_id"

        finally:
            # Restore original env vars
            if original_access:
                os.environ["SALESFORCE_ACCESS_TOKEN"] = original_access
            else:
                os.environ.pop("SALESFORCE_ACCESS_TOKEN", None)
            if original_instance:
                os.environ["SALESFORCE_INSTANCE_URL"] = original_instance
            else:
                os.environ.pop("SALESFORCE_INSTANCE_URL", None)
            if original_user_id:
                os.environ["SALESFORCE_USER_ID"] = original_user_id
            else:
                os.environ.pop("SALESFORCE_USER_ID", None)
            if original_org_id:
                os.environ["SALESFORCE_ORG_ID"] = original_org_id
            else:
                os.environ.pop("SALESFORCE_ORG_ID", None)
            if original_username:
                os.environ["SALESFORCE_USERNAME"] = original_username
            else:
                os.environ.pop("SALESFORCE_USERNAME", None)

    def test_get_token_no_source(self):
        """Test getting token when no source is available."""
        # Save original env vars
        original_access = os.environ.get("SALESFORCE_ACCESS_TOKEN")
        original_instance = os.environ.get("SALESFORCE_INSTANCE_URL")

        try:
            # Clear relevant env vars
            os.environ.pop("SALESFORCE_ACCESS_TOKEN", None)
            os.environ.pop("SALESFORCE_INSTANCE_URL", None)

            # Mock the fastmcp import to fail (simulates no OAuth context)
            with patch.dict("sys.modules", {"fastmcp.server.dependencies": None}):
                token_info = get_salesforce_token()

            assert token_info is None

        finally:
            # Restore original env vars
            if original_access:
                os.environ["SALESFORCE_ACCESS_TOKEN"] = original_access
            if original_instance:
                os.environ["SALESFORCE_INSTANCE_URL"] = original_instance
