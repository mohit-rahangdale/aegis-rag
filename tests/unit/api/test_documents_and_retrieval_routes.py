"""Unit tests for document upload and retrieval search endpoints."""

import io
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.ingestion.models import IngestionResult
from app.retrieval.models import RetrievedChunk


def test_upload_document_success(client: TestClient):
    """Verify document upload endpoint calls pipeline and returns IngestionResult."""
    fake_result = IngestionResult(
        document_id="00000000-0000-0000-0000-000000000001",
        filename="test.txt",
        status="processed",
        checksum="abcd1234checksum",
        chunk_count=3,
        file_size_bytes=100,
        is_duplicate=False,
    )

    with patch(
        "app.api.routes.documents.IngestionPipeline.ingest_document",
        new_callable=AsyncMock,
        return_value=fake_result,
    ):
        file_content = b"Sample text content for test."
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post("/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "processed"
        assert data["chunk_count"] == 3
        assert data["filename"] == "test.txt"


def test_upload_unsupported_extension_rejected(client: TestClient):
    """Verify upload rejects unsupported file extensions."""
    files = {"file": ("malicious.exe", io.BytesIO(b"binary data"), "application/octet-stream")}
    response = client.post("/documents/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_retrieval_search_endpoint(client: TestClient):
    """Verify POST /retrieval/search returns formatted results."""
    mock_chunk = RetrievedChunk(
        chunk_id="chunk_1",
        document_id="doc_1",
        text="AegisRAG features multi-LLM failover.",
        score=0.95,
        source="hybrid",
    )

    with patch(
        "app.retrieval.hybrid.HybridRetriever.retrieve",
        new_callable=AsyncMock,
        return_value=[mock_chunk],
    ):
        payload = {
            "query": "multi-LLM failover",
            "top_k": 3,
            "enable_reranking": False,
        }
        response = client.post("/retrieval/search", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "multi-LLM failover"
        assert data["total_found"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["chunk_id"] == "chunk_1"
