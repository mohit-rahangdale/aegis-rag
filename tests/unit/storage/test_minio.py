"""Unit tests for MinIO object storage service."""

import io
import pytest

from app.storage.minio.service import MinioStorageService


class MockMinioResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self):
        pass

    def release_conn(self):
        pass


class MockMinioClient:
    """Mock MinIO client for testing storage operations without a live MinIO server."""

    def __init__(self):
        self.buckets = set(["test-bucket"])
        self.objects = {}

    def bucket_exists(self, bucket_name: str) -> bool:
        return bucket_name in self.buckets

    def make_bucket(self, bucket_name: str):
        self.buckets.add(bucket_name)

    def list_buckets(self):
        return list(self.buckets)

    def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str):
        self.objects[(bucket_name, object_name)] = data.read()

    def get_object(self, bucket_name: str, object_name: str):
        if (bucket_name, object_name) not in self.objects:
            raise Exception("NoSuchKey")
        return MockMinioResponse(self.objects[(bucket_name, object_name)])

    def stat_object(self, bucket_name: str, object_name: str):
        if (bucket_name, object_name) not in self.objects:
            from minio.error import S3Error
            raise S3Error(
                code="NoSuchKey",
                message="Object does not exist",
                resource=object_name,
                request_id="123",
                host_id="localhost",
                response=None,
            )
        return True

    def remove_object(self, bucket_name: str, object_name: str):
        self.objects.pop((bucket_name, object_name), None)


@pytest.mark.anyio
async def test_minio_upload_and_download():
    """Verify upload and download of binary/text file data."""
    mock_client = MockMinioClient()
    service = MinioStorageService(client=mock_client, default_bucket="test-bucket")

    test_content = b"Sample document content for AegisRAG"
    path = await service.upload_bytes("docs/sample.txt", test_content, content_type="text/plain")
    assert path == "test-bucket/docs/sample.txt"

    # Check existence
    assert await service.object_exists("docs/sample.txt") is True

    # Download bytes
    downloaded = await service.download_bytes("docs/sample.txt")
    assert downloaded == test_content

    # Delete
    deleted = await service.delete_object("docs/sample.txt")
    assert deleted is True
    assert await service.object_exists("docs/sample.txt") is False


@pytest.mark.anyio
async def test_minio_health_check():
    """Verify MinIO health check succeeds when buckets can be listed."""
    mock_client = MockMinioClient()
    service = MinioStorageService(client=mock_client)
    assert await service.is_healthy() is True
