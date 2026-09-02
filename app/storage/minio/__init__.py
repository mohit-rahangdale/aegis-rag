"""MinIO object storage package."""

from app.storage.minio.client import get_minio_client
from app.storage.minio.service import MinioStorageService

__all__ = ["get_minio_client", "MinioStorageService"]
