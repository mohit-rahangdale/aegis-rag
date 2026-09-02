"""Unit tests for root and health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


def test_root_endpoint(client: TestClient):
    """Test GET / returns operational status and service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "aegisrag" in data["service"]
    assert "version" in data
    assert "docs_url" in data
    assert response.headers.get("X-Request-ID") is not None
    assert response.headers.get("X-Process-Time-Ms") is not None


def test_health_endpoint(client: TestClient):
    """Test GET /health returns status and service information."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "aegisrag" in data["service"]
    assert "version" in data
    assert "environment" in data


def test_prefixed_health_endpoint(client: TestClient):
    """Test GET /api/v1/health returns valid operational status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")


def test_request_id_propagation(client: TestClient):
    """Test that custom X-Request-ID is preserved and returned in headers."""
    custom_id = "test-custom-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.anyio
async def test_async_health_endpoint(async_client: AsyncClient):
    """Test async health check via AsyncClient."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "aegisrag" in data["service"]



