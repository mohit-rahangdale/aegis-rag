"""Object storage service for uploading, downloading, and managing files in MinIO."""

import asyncio
import io
from typing import Any, Dict, Optional

from minio import Minio
from minio.error import S3Error

from app.config.settings import get_settings
from app.storage.minio.client import (
    check_minio_health,
    ensure_bucket_exists,
    get_minio_client,
)


class MinioStorageService:
    """Storage service providing async abstractions for S3/MinIO operations."""

    def __init__(
        self,
        client: Optional[Minio] = None,
        default_bucket: Optional[str] = None,
    ) -> None:
        self._client = client
        self.default_bucket = default_bucket or get_settings().minio_bucket

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = get_minio_client()
        return self._client

    async def initialize_bucket(self, bucket: Optional[str] = None) -> bool:
        """Ensure the target bucket is created."""
        target_bucket = bucket or self.default_bucket
        return await ensure_bucket_exists(target_bucket, self.client)

    async def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None,
    ) -> str:
        """Upload raw bytes to MinIO and return the storage path."""
        target_bucket = bucket or self.default_bucket

        def _upload() -> str:
            # Auto-ensure bucket exists
            if not self.client.bucket_exists(target_bucket):
                self.client.make_bucket(target_bucket)

            stream = io.BytesIO(data)
            self.client.put_object(
                bucket_name=target_bucket,
                object_name=object_name,
                data=stream,
                length=len(data),
                content_type=content_type,
            )
            return f"{target_bucket}/{object_name}"

        return await asyncio.to_thread(_upload)

    async def download_bytes(
        self,
        object_name: str,
        bucket: Optional[str] = None,
    ) -> bytes:
        """Download object content as bytes."""
        target_bucket = bucket or self.default_bucket

        def _download() -> bytes:
            response = self.client.get_object(target_bucket, object_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_download)

    async def delete_object(
        self,
        object_name: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """Delete an object from storage."""
        target_bucket = bucket or self.default_bucket

        def _delete() -> bool:
            self.client.remove_object(target_bucket, object_name)
            return True

        try:
            return await asyncio.to_thread(_delete)
        except Exception:
            return False

    async def object_exists(
        self,
        object_name: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """Check if an object exists in storage."""
        target_bucket = bucket or self.default_bucket

        def _exists() -> bool:
            try:
                self.client.stat_object(target_bucket, object_name)
                return True
            except S3Error as err:
                if err.code in ("NoSuchKey", "NoSuchBucket"):
                    return False
                raise

        try:
            return await asyncio.to_thread(_exists)
        except Exception:
            return False

    async def is_healthy(self) -> bool:
        """Verify storage health."""
        return await check_minio_health(self.client)
