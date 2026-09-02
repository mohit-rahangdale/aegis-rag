"""Pytest configuration and shared fixtures for AegisRAG tests."""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config.settings import Settings, get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Fixture providing testing settings."""
    return Settings(
        app_name="aegisrag-test",
        app_version="0.1.0",
        app_env="testing",
        debug=True,
        log_level="DEBUG",
        log_format="text",
    )


@pytest.fixture
def test_app(test_settings: Settings):
    """Fixture providing a test FastAPI application instance."""
    app = create_app(settings=test_settings)
    return app


@pytest.fixture
def client(test_app) -> TestClient:
    """Fixture providing a synchronous TestClient."""
    return TestClient(test_app)


@pytest.fixture
async def async_client(test_app) -> AsyncClient:
    """Fixture providing an asynchronous HTTPX client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
