"""Tests for the OAuth storage backend configuration."""

import os
from unittest.mock import MagicMock, patch

import pytest

from salesforce_mcp_server.oauth.storage import create_storage


class TestCreateStorage:
    """Tests for create_storage factory function."""

    def test_default_memory_storage(self):
        """Test that memory storage is created by default."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing storage type setting
            os.environ.pop("OAUTH_STORAGE_TYPE", None)
            os.environ.pop("STORAGE_ENCRYPTION_KEY", None)

            storage = create_storage()

            # Check it's a MemoryStore
            assert storage.__class__.__name__ == "MemoryStore"

    def test_explicit_memory_storage(self):
        """Test creating memory storage explicitly."""
        with patch.dict(os.environ, {"OAUTH_STORAGE_TYPE": "memory"}, clear=True):
            storage = create_storage()

            assert storage.__class__.__name__ == "MemoryStore"

    def test_memory_storage_case_insensitive(self):
        """Test that storage type is case insensitive."""
        with patch.dict(os.environ, {"OAUTH_STORAGE_TYPE": "MEMORY"}, clear=True):
            storage = create_storage()

            assert storage.__class__.__name__ == "MemoryStore"

    def test_redis_storage(self):
        """Test creating Redis storage."""
        mock_redis_store = MagicMock()
        mock_redis_store_class = MagicMock()
        mock_redis_store_class.from_url.return_value = mock_redis_store

        with patch.dict(
            os.environ,
            {"OAUTH_STORAGE_TYPE": "redis", "REDIS_URL": "redis://localhost:6379"},
            clear=True,
        ):
            with patch("key_value.aio.stores.redis.RedisStore", mock_redis_store_class):
                storage = create_storage()

                mock_redis_store_class.from_url.assert_called_once_with(
                    "redis://localhost:6379"
                )
                assert storage == mock_redis_store

    def test_redis_storage_default_url(self):
        """Test Redis storage uses default URL when not specified."""
        mock_redis_store = MagicMock()
        mock_redis_store_class = MagicMock()
        mock_redis_store_class.from_url.return_value = mock_redis_store

        with patch.dict(
            os.environ,
            {"OAUTH_STORAGE_TYPE": "redis"},
            clear=True,
        ):
            # Ensure REDIS_URL is not set
            os.environ.pop("REDIS_URL", None)

            with patch("key_value.aio.stores.redis.RedisStore", mock_redis_store_class):
                create_storage()

                mock_redis_store_class.from_url.assert_called_once_with(
                    "redis://localhost:6379"
                )

    def test_unknown_storage_type_raises_error(self):
        """Test that unknown storage type raises ValueError."""
        with patch.dict(os.environ, {"OAUTH_STORAGE_TYPE": "unknown"}, clear=True):
            with pytest.raises(ValueError, match="Unknown storage type: unknown"):
                create_storage()

    def test_encryption_wrapper_applied(self):
        """Test that encryption wrapper is applied when key is provided."""
        # Generate a valid Fernet key for testing
        from cryptography.fernet import Fernet

        test_key = Fernet.generate_key().decode()

        with patch.dict(
            os.environ,
            {"OAUTH_STORAGE_TYPE": "memory", "STORAGE_ENCRYPTION_KEY": test_key},
            clear=True,
        ):
            storage = create_storage()

            # Check it's wrapped with FernetEncryptionWrapper
            assert storage.__class__.__name__ == "FernetEncryptionWrapper"

    def test_redis_with_encryption(self):
        """Test Redis storage with encryption wrapper."""
        from cryptography.fernet import Fernet

        test_key = Fernet.generate_key().decode()

        mock_redis_store = MagicMock()
        mock_redis_store_class = MagicMock()
        mock_redis_store_class.from_url.return_value = mock_redis_store

        with patch.dict(
            os.environ,
            {
                "OAUTH_STORAGE_TYPE": "redis",
                "REDIS_URL": "redis://localhost:6379",
                "STORAGE_ENCRYPTION_KEY": test_key,
            },
            clear=True,
        ):
            with patch("key_value.aio.stores.redis.RedisStore", mock_redis_store_class):
                storage = create_storage()

                # Should be wrapped with encryption
                assert storage.__class__.__name__ == "FernetEncryptionWrapper"
