"""Health check routes for service monitoring and orchestration readiness."""

from typing import Dict, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.config.settings import get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Standard health check response model."""

    status: str = Field(..., description="Overall health status of the service", example="healthy")
    service: str = Field(..., description="Service identifier", example="aegisrag")
    version: str = Field(..., description="Application version", example="0.1.0")
    environment: str = Field(..., description="Active runtime environment", example="development")
    dependencies: Optional[Dict[str, str]] = Field(
        default=None,
        description="Health status of external dependencies",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health status of AegisRAG and its downstream dependencies.",
)
async def get_health() -> HealthResponse:
    """Return the health status of the service."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
