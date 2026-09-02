"""Qdrant client initialization and connection management."""

from typing import Optional

from qdrant_client import AsyncQdrantClient

from app.config.settings import Settings, get_settings

_qdrant_client: Optional[AsyncQdrantClient] = None


def get_qdrant_client(
    settings: Optional[Settings] = None,
    in_memory: bool = False,
) -> AsyncQdrantClient:
    """Return an asynchronous Qdrant client instance.

    Uses Qdrant Cloud when url/api_key is configured in settings.
    Falls back to an in-memory client for testing or offline environments.
    """
    global _qdrant_client
    if in_memory:
        return AsyncQdrantClient(":memory:")

    if _qdrant_client is None:
        if settings is None:
            settings = get_settings()

        if settings.qdrant_url:
            _qdrant_client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=10.0,
            )
        else:
            # Fallback for local development/testing without live cloud cluster
            _qdrant_client = AsyncQdrantClient(":memory:")

    return _qdrant_client


async def check_qdrant_health(client: Optional[AsyncQdrantClient] = None) -> bool:
    """Probe Qdrant connectivity and health."""
    try:
        if client is None:
            client = get_qdrant_client()
        # Querying collections serves as a lightweight health check
        await client.get_collections()
        return True
    except Exception:
        return False


async def close_qdrant() -> None:
    """Close the active Qdrant client."""
    global _qdrant_client
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
