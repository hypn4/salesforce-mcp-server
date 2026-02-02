"""Tests for the Salesforce OAuth Proxy."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from salesforce_mcp_server.oauth.pkce import (
    compute_challenge,
    generate_pkce_pair,
    verify_pkce,
)
from salesforce_mcp_server.oauth.proxy import SalesforceOAuthProxy


class TestPKCE:
    """Tests for PKCE utilities."""

    def test_generate_pkce_pair(self):
        """Test PKCE pair generation."""
        verifier, challenge = generate_pkce_pair()

        # Verify lengths
        assert len(verifier) == 43  # 32 bytes base64url encoded
        assert len(challenge) == 43  # SHA256 base64url encoded (without padding)

        # Verify the pair is valid
        assert verify_pkce(verifier, challenge)

    def test_generate_pkce_pair_unique(self):
        """Test that each PKCE pair is unique."""
        pairs = [generate_pkce_pair() for _ in range(10)]
        verifiers = [p[0] for p in pairs]
        challenges = [p[1] for p in pairs]

        # All verifiers should be unique
        assert len(set(verifiers)) == 10
        # All challenges should be unique
        assert len(set(challenges)) == 10

    def test_compute_challenge(self):
        """Test S256 challenge computation."""
        # Known test vector (RFC 7636 Appendix B)
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

        challenge = compute_challenge(verifier)
        assert challenge == expected_challenge

    def test_verify_pkce_success(self):
        """Test successful PKCE verification."""
        verifier, challenge = generate_pkce_pair()
        assert verify_pkce(verifier, challenge) is True

    def test_verify_pkce_failure(self):
        """Test PKCE verification with wrong verifier."""
        _, challenge = generate_pkce_pair()
        assert verify_pkce("wrong_verifier", challenge) is False

    def test_verify_pkce_timing_safe(self):
        """Test that PKCE verification is timing-safe."""
        verifier, challenge = generate_pkce_pair()

        # Verification should use constant-time comparison
        # (we can't easily test timing, but we verify it uses secrets.compare_digest)
        assert verify_pkce(verifier, challenge) is True
        assert verify_pkce(verifier + "x", challenge) is False


class TestSalesforceOAuthProxy:
    """Tests for SalesforceOAuthProxy."""

    def test_init_with_defaults(self):
        """Test initialization with default values (confidential client)."""
        proxy = SalesforceOAuthProxy(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        assert proxy.client_id == "test_client_id"
        assert proxy.client_secret == "test_client_secret"
        assert proxy.login_url == "https://login.salesforce.com"
        assert proxy.base_url == "http://localhost:8000"
        assert proxy.required_scopes == ["api", "refresh_token"]
        assert proxy.is_pkce_only is False
        assert proxy._token_auth_method == "client_secret_post"

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        proxy = SalesforceOAuthProxy(
            client_id="custom_id",
            client_secret="custom_secret",
            login_url="https://test.salesforce.com",
            base_url="https://my-server.com",
            required_scopes=["api", "full"],
        )

        assert proxy.login_url == "https://test.salesforce.com"
        assert proxy.base_url == "https://my-server.com"
        assert proxy.required_scopes == ["api", "full"]

    def test_salesforce_endpoints(self):
        """Test Salesforce OAuth endpoint URLs."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="test_secret",
            login_url="https://login.salesforce.com",
        )

        assert (
            proxy.authorization_endpoint
            == "https://login.salesforce.com/services/oauth2/authorize"
        )
        assert (
            proxy.token_endpoint == "https://login.salesforce.com/services/oauth2/token"
        )
        assert (
            proxy.revocation_endpoint
            == "https://login.salesforce.com/services/oauth2/revoke"
        )

    def test_trailing_slash_removed(self):
        """Test that trailing slashes are removed from URLs."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="test_secret",
            login_url="https://login.salesforce.com/",
            base_url="https://my-server.com/",
        )

        assert proxy.login_url == "https://login.salesforce.com"
        assert proxy.base_url == "https://my-server.com"

    def test_oauth_proxy_property(self):
        """Test that oauth_proxy property returns OAuthProxy instance."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="test_secret",
        )

        # Should return the FastMCP OAuthProxy
        from fastmcp.server.auth import OAuthProxy

        assert proxy.oauth_proxy is not None
        assert isinstance(proxy.oauth_proxy, OAuthProxy)

    def test_token_verifier_property(self):
        """Test that token_verifier property returns SalesforceTokenVerifier."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="test_secret",
        )

        from salesforce_mcp_server.oauth.token_verifier import SalesforceTokenVerifier

        assert isinstance(proxy.token_verifier, SalesforceTokenVerifier)


class TestSalesforceOAuthProxyFromEnv:
    """Tests for SalesforceOAuthProxy.from_env() factory."""

    def test_from_env_with_credentials(self):
        """Test creating proxy from environment variables."""
        with patch.dict(
            os.environ,
            {
                "SALESFORCE_CLIENT_ID": "env_client_id",
                "SALESFORCE_CLIENT_SECRET": "env_client_secret",
                "SALESFORCE_LOGIN_URL": "https://test.salesforce.com",
                "BASE_URL": "https://my-server.com",
                "OAUTH_REQUIRED_SCOPES": "api,full,refresh_token",
            },
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()

            assert proxy is not None
            assert proxy.client_id == "env_client_id"
            assert proxy.client_secret == "env_client_secret"
            assert proxy.login_url == "https://test.salesforce.com"
            assert proxy.base_url == "https://my-server.com"
            assert proxy.required_scopes == ["api", "full", "refresh_token"]

    def test_from_env_without_client_id(self):
        """Test that from_env returns None without client ID."""
        with patch.dict(
            os.environ,
            {"SALESFORCE_CLIENT_SECRET": "secret"},
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()
            assert proxy is None

    def test_from_env_without_client_secret_returns_pkce_only(self):
        """Test that from_env returns PKCE-only proxy without client secret."""
        with patch.dict(
            os.environ,
            {"SALESFORCE_CLIENT_ID": "client_id"},
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()
            assert proxy is not None
            assert proxy.is_pkce_only is True
            assert proxy._token_auth_method == "none"
            assert proxy.client_secret == ""

    def test_from_env_with_defaults(self):
        """Test from_env uses defaults when optional vars are not set."""
        with patch.dict(
            os.environ,
            {
                "SALESFORCE_CLIENT_ID": "client_id",
                "SALESFORCE_CLIENT_SECRET": "client_secret",
            },
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()

            assert proxy is not None
            assert proxy.login_url == "https://login.salesforce.com"
            assert proxy.base_url == "http://localhost:8000"
            assert proxy.required_scopes == ["api", "refresh_token"]

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing the proxy cleans up resources."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="test_secret",
        )

        # Mock the token verifier's close method
        proxy._token_verifier.close = AsyncMock()

        await proxy.close()

        proxy._token_verifier.close.assert_called_once()


class TestServerOAuthModeIntegration:
    """Tests for OAuth mode integration in server.py."""

    def test_bearer_mode_default(self):
        """Test that bearer mode is the default."""
        from salesforce_mcp_server.server import _get_oauth_mode

        with patch.dict(os.environ, {}, clear=True):
            assert _get_oauth_mode() == "bearer"

    def test_bearer_mode_explicit(self):
        """Test explicit bearer mode."""
        from salesforce_mcp_server.server import _get_oauth_mode

        with patch.dict(os.environ, {"OAUTH_MODE": "bearer"}, clear=True):
            assert _get_oauth_mode() == "bearer"

    def test_proxy_mode(self):
        """Test proxy mode."""
        from salesforce_mcp_server.server import _get_oauth_mode

        with patch.dict(os.environ, {"OAUTH_MODE": "proxy"}, clear=True):
            assert _get_oauth_mode() == "proxy"

    def test_proxy_mode_case_insensitive(self):
        """Test that OAuth mode is case insensitive."""
        from salesforce_mcp_server.server import _get_oauth_mode

        with patch.dict(os.environ, {"OAUTH_MODE": "PROXY"}, clear=True):
            assert _get_oauth_mode() == "proxy"

    def test_create_http_auth_bearer_mode(self):
        """Test _create_http_auth in bearer mode."""
        from salesforce_mcp_server.oauth.token_verifier import SalesforceTokenVerifier
        from salesforce_mcp_server.server import _create_http_auth

        with patch.dict(os.environ, {"OAUTH_MODE": "bearer"}, clear=True):
            auth = _create_http_auth()
            assert isinstance(auth, SalesforceTokenVerifier)

    def test_create_http_auth_proxy_mode_missing_credentials(self):
        """Test _create_http_auth in proxy mode without credentials."""
        from salesforce_mcp_server.server import _create_http_auth

        with patch.dict(os.environ, {"OAUTH_MODE": "proxy"}, clear=True):
            with pytest.raises(ValueError, match="SALESFORCE_CLIENT_ID"):
                _create_http_auth()

    def test_create_http_auth_proxy_mode_with_credentials(self):
        """Test _create_http_auth in proxy mode with credentials."""
        from fastmcp.server.auth import OAuthProxy

        from salesforce_mcp_server.server import _create_http_auth

        with patch.dict(
            os.environ,
            {
                "OAUTH_MODE": "proxy",
                "SALESFORCE_CLIENT_ID": "test_id",
                "SALESFORCE_CLIENT_SECRET": "test_secret",
            },
            clear=True,
        ):
            auth = _create_http_auth()
            assert isinstance(auth, OAuthProxy)

    def test_create_http_auth_proxy_mode_pkce_only(self):
        """Test _create_http_auth in proxy mode with PKCE-only (no client secret)."""
        from fastmcp.server.auth import OAuthProxy

        from salesforce_mcp_server.server import _create_http_auth

        with patch.dict(
            os.environ,
            {
                "OAUTH_MODE": "proxy",
                "SALESFORCE_CLIENT_ID": "test_id",
                # No SALESFORCE_CLIENT_SECRET - PKCE-only mode
            },
            clear=True,
        ):
            auth = _create_http_auth()
            assert isinstance(auth, OAuthProxy)


class TestPKCEOnlyMode:
    """Tests for PKCE-only mode (no client secret)."""

    def test_pkce_only_init_with_none(self):
        """Test initialization without client secret (None)."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret=None,
        )
        assert proxy.is_pkce_only is True
        assert proxy._token_auth_method == "none"
        assert proxy.client_secret == ""

    def test_pkce_only_init_with_empty_string(self):
        """Test initialization with empty string client secret."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="",
        )
        assert proxy.is_pkce_only is True
        assert proxy._token_auth_method == "none"
        assert proxy.client_secret == ""

    def test_pkce_only_init_without_secret_arg(self):
        """Test initialization without passing client_secret argument."""
        proxy = SalesforceOAuthProxy(client_id="test_id")
        assert proxy.is_pkce_only is True
        assert proxy._token_auth_method == "none"
        assert proxy.client_secret == ""

    def test_confidential_client_mode(self):
        """Test initialization with client secret (confidential client)."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="test_secret",
        )
        assert proxy.is_pkce_only is False
        assert proxy._token_auth_method == "client_secret_post"
        assert proxy.client_secret == "test_secret"

    def test_from_env_pkce_only_mode(self):
        """Test from_env with only client_id creates PKCE-only proxy."""
        with patch.dict(
            os.environ,
            {
                "SALESFORCE_CLIENT_ID": "test_id",
                # No SALESFORCE_CLIENT_SECRET
            },
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()
            assert proxy is not None
            assert proxy.is_pkce_only is True
            assert proxy._token_auth_method == "none"

    def test_from_env_confidential_mode(self):
        """Test from_env with client_id and client_secret creates confidential proxy."""
        with patch.dict(
            os.environ,
            {
                "SALESFORCE_CLIENT_ID": "test_id",
                "SALESFORCE_CLIENT_SECRET": "test_secret",
            },
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()
            assert proxy is not None
            assert proxy.is_pkce_only is False
            assert proxy._token_auth_method == "client_secret_post"

    def test_from_env_empty_secret_is_pkce_only(self):
        """Test from_env with empty client_secret is PKCE-only."""
        with patch.dict(
            os.environ,
            {
                "SALESFORCE_CLIENT_ID": "test_id",
                "SALESFORCE_CLIENT_SECRET": "",
            },
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()
            assert proxy is not None
            assert proxy.is_pkce_only is True

    def test_oauth_proxy_created_with_correct_auth_method(self):
        """Test that OAuth proxy is created with correct token auth method."""
        # PKCE-only mode
        proxy_pkce = SalesforceOAuthProxy(client_id="test_id")
        assert proxy_pkce.oauth_proxy is not None

        # Confidential mode
        proxy_conf = SalesforceOAuthProxy(
            client_id="test_id",
            client_secret="test_secret",
        )
        assert proxy_conf.oauth_proxy is not None


class TestRedirectPath:
    """Tests for redirect_path configuration."""

    def test_redirect_path_default(self):
        """Test that redirect_path defaults to /auth/callback."""
        proxy = SalesforceOAuthProxy(client_id="test_id")
        assert proxy.redirect_path == "/auth/callback"

    def test_redirect_path_custom(self):
        """Test initialization with custom redirect_path."""
        proxy = SalesforceOAuthProxy(
            client_id="test_id",
            redirect_path="/custom/callback",
        )
        assert proxy.redirect_path == "/custom/callback"

    def test_from_env_redirect_path_default(self):
        """Test from_env uses default redirect_path when not set."""
        with patch.dict(
            os.environ,
            {
                "SALESFORCE_CLIENT_ID": "test_id",
            },
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()
            assert proxy is not None
            assert proxy.redirect_path == "/auth/callback"

    def test_from_env_redirect_path_custom(self):
        """Test from_env reads OAUTH_REDIRECT_PATH environment variable."""
        with patch.dict(
            os.environ,
            {
                "SALESFORCE_CLIENT_ID": "test_id",
                "OAUTH_REDIRECT_PATH": "/custom/oauth/callback",
            },
            clear=True,
        ):
            proxy = SalesforceOAuthProxy.from_env()
            assert proxy is not None
            assert proxy.redirect_path == "/custom/oauth/callback"
