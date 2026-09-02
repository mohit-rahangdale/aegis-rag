"""MinIO client initialization and bucket management."""

import asyncio
from typing import Optional

import urllib3
from minio import Minio

from app.config.settings import Settings, get_settings

_minio_client: Optional[Minio] = None


def get_minio_client(settings: Optional[Settings] = None) -> Minio:
    """Return a singleton MinIO client instance."""
    global _minio_client
    if _minio_client is None:
        if settings is None:
            settings = get_settings()

        http_client = urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=0.2, read=0.5),
            retries=False,
        )


        _minio_client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            http_client=http_client,
        )
    return _minio_client



async def ensure_bucket_exists(bucket_name: str, client: Optional[Minio] = None) -> bool:
    """Verify that a bucket exists, creating it if necessary."""
    if client is None:
        client = get_minio_client()

    def _ensure() -> bool:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        return True

    try:
        return await asyncio.to_thread(_ensure)
    except Exception:
        return False


async def check_minio_health(client: Optional[Minio] = None) -> bool:
    """Verify that MinIO service is reachable and responsive."""
    if client is None:
        client = get_minio_client()

    def _check() -> bool:
        # Listing buckets is a lightweight probe
        client.list_buckets()
        return True

    try:
        return await asyncio.to_thread(_check)
    except Exception:
        return False
