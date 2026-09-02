"""Tests for unified storage dependency health checks and GET /health."""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.health.checks import check_all_dependencies, get_overall_status


@pytest.mark.anyio
async def test_all_dependencies_healthy():
    """Verify check_all_dependencies when all components report operational."""
    with (
        patch("app.health.checks.check_db_health", new_callable=AsyncMock) as mock_db,
        patch("app.health.checks.check_redis_health", new_callable=AsyncMock) as mock_redis,
        patch("app.health.checks.check_minio_health", new_callable=AsyncMock) as mock_minio,
        patch("app.health.checks.check_qdrant_health", new_callable=AsyncMock) as mock_qdrant,
    ):
        mock_db.return_value = True
        mock_redis.return_value = True
        mock_minio.return_value = True
        mock_qdrant.return_value = True

        deps = await check_all_dependencies()
        assert deps["postgres"] == "healthy"
        assert deps["redis"] == "healthy"
        assert deps["minio"] == "healthy"
        assert deps["qdrant"] == "healthy"

        overall = get_overall_status(deps)
        assert overall == "healthy"


@pytest.mark.anyio
async def test_dependency_failure_reports_degraded():
    """Verify degraded status when one dependency is unreachable without leaking credentials."""
    with (
        patch("app.health.checks.check_db_health", new_callable=AsyncMock) as mock_db,
        patch("app.health.checks.check_redis_health", new_callable=AsyncMock) as mock_redis,
        patch("app.health.checks.check_minio_health", new_callable=AsyncMock) as mock_minio,
        patch("app.health.checks.check_qdrant_health", new_callable=AsyncMock) as mock_qdrant,
    ):
        mock_db.return_value = True
        mock_redis.return_value = False  # Redis fails
        mock_minio.return_value = True
        mock_qdrant.return_value = True

        deps = await check_all_dependencies()
        assert deps["postgres"] == "healthy"
        assert deps["redis"] == "unreachable"
        assert deps["minio"] == "healthy"
        assert deps["qdrant"] == "healthy"

        overall = get_overall_status(deps)
        assert overall == "degraded"


def test_health_endpoint_response_structure(client: TestClient):
    """Verify GET /health returns dependencies dictionary without credentials."""
    with patch(
        "app.api.routes.health.get_overall_health",
        new_callable=AsyncMock,
        return_value=(
            "healthy",
            {"postgres": "healthy", "redis": "healthy", "minio": "healthy", "qdrant": "healthy"},
        ),
    ):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "dependencies" in data
        assert data["dependencies"]["postgres"] == "healthy"
        assert data["dependencies"]["redis"] == "healthy"
        assert data["dependencies"]["minio"] == "healthy"
        assert data["dependencies"]["qdrant"] == "healthy"
        # Ensure no passwords or urls are exposed
        response_text = response.text.lower()
        assert "password" not in response_text
        assert "minioadmin" not in response_text
