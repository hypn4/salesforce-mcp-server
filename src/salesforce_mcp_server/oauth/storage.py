"""OAuth storage backend configuration.

Provides factory function to create appropriate storage backend
for OAuth proxy token and client data storage.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..logging_config import get_logger

if TYPE_CHECKING:
    from key_value.aio.protocols.key_value import AsyncKeyValue

logger = get_logger("oauth.storage")


def create_storage() -> "AsyncKeyValue":
    """Create storage backend based on environment configuration.

    Storage type is determined by OAUTH_STORAGE_TYPE environment variable:
    - 'memory' (default): In-memory storage (for development/testing)
    - 'redis': Redis-based storage (for production with persistence)

    If STORAGE_ENCRYPTION_KEY is set, storage will be wrapped with
    Fernet encryption for secure token storage.

    Environment variables:
        OAUTH_STORAGE_TYPE: Storage type ('memory' or 'redis')
        REDIS_URL: Redis connection URL (default: redis://localhost:6379)
        STORAGE_ENCRYPTION_KEY: Fernet key for encryption (optional)

    Returns:
        AsyncKeyValue: Configured storage backend

    Raises:
        ValueError: If unknown storage type is specified
    """
    storage_type = os.getenv("OAUTH_STORAGE_TYPE", "memory").lower()
    encryption_key = os.getenv("STORAGE_ENCRYPTION_KEY")

    logger.info(
        "Creating storage backend: type=%s, encrypted=%s",
        storage_type,
        bool(encryption_key),
    )

    if storage_type == "memory":
        from key_value.aio.stores.memory import MemoryStore

        storage: AsyncKeyValue = MemoryStore()
        logger.debug("Created in-memory storage backend")

    elif storage_type == "redis":
        from key_value.aio.stores.redis import RedisStore

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        storage = RedisStore(url=redis_url)
        logger.debug("Created Redis storage backend: url=%s", redis_url)

    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

    # Apply encryption wrapper if key is provided
    if encryption_key:
        from cryptography.fernet import Fernet
        from key_value.aio.wrappers.encryption.fernet import FernetEncryptionWrapper

        # If the key looks like a Fernet key (base64, 44 chars), use it directly
        # Otherwise, use it as source material for key derivation
        try:
            fernet = Fernet(encryption_key.encode())
            storage = FernetEncryptionWrapper(storage, fernet=fernet)
        except Exception:
            storage = FernetEncryptionWrapper(storage, source_material=encryption_key)
        logger.debug("Applied Fernet encryption wrapper to storage")

    return storage
