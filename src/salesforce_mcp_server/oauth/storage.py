"""OAuth storage backend configuration.

Provides factory function to create storage backends for OAuthProxy
based on environment configuration.
"""

from __future__ import annotations

import os
from typing import Any


def create_storage() -> Any:
    """Create storage backend based on configuration.

    Environment variables:
        OAUTH_STORAGE_TYPE: "memory" | "redis" (default: "memory")
        REDIS_URL: Redis connection URL (required for redis type)
        STORAGE_ENCRYPTION_KEY: Fernet key for encryption (optional)

    Returns:
        Configured storage backend instance

    Raises:
        ValueError: If an unknown storage type is specified
    """
    from key_value.aio.stores.memory import MemoryStore

    storage_type = os.getenv("OAUTH_STORAGE_TYPE", "memory").lower()
    encryption_key = os.getenv("STORAGE_ENCRYPTION_KEY")

    if storage_type == "memory":
        store: Any = MemoryStore()
    elif storage_type == "redis":
        from key_value.aio.stores.redis import RedisStore

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        store = RedisStore.from_url(redis_url)  # type: ignore[attr-defined]
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

    # Apply encryption wrapper if key is provided
    if encryption_key:
        from cryptography.fernet import Fernet
        from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

        store = FernetEncryptionWrapper(
            key_value=store,
            fernet=Fernet(encryption_key.encode()),
        )

    return store
