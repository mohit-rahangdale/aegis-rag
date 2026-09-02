"""Main application module for AegisRAG.

Initializes FastAPI, configures middlewares, lifespan handlers, and registers routes.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import __version__
from app.api.routes.health import router as health_router
from app.config.settings import Settings, get_settings
from app.core.logging import get_logger, setup_logging

logger = get_logger("aegisrag.main")


class RootResponse(BaseModel):
    """Response model for the root endpoint."""

    service: str = Field(..., description="Service identifier", example="aegisrag")
    version: str = Field(..., description="Service version", example="0.1.0")
    status: str = Field(..., description="Operational status", example="operational")
    docs_url: str = Field(..., description="Interactive OpenAPI documentation URL", example="/docs")
    environment: str = Field(..., description="Running environment", example="development")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings)

    logger.info(
        "AegisRAG service starting up",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "debug": settings.debug,
        },
    )

    yield

    logger.info("AegisRAG service shutting down cleanly")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for AegisRAG."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="AegisRAG",
        description=(
            "Production-grade Corrective RAG and Agentic AI platform with multi-LLM failover, "
            "hybrid retrieval, reranking, AI guardrails, memory, evaluation, and LLMOps."
        ),
        version=settings.app_version or __version__,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and Timing Middleware
    @app.middleware("http")
    async def request_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time * 1000:.2f}"
        return response

    # Include health router at root /health
    app.include_router(health_router)

    # Include versioned API router if needed
    app.include_router(health_router, prefix=settings.api_prefix)

    @app.get(
        "/",
        response_model=RootResponse,
        status_code=status.HTTP_200_OK,
        tags=["General"],
        summary="Service Root",
        description="Root endpoint providing service status and metadata.",
    )
    async def root() -> RootResponse:
        """Root endpoint returning service identity and status."""
        return RootResponse(
            service=settings.app_name,
            version=settings.app_version,
            status="operational",
            docs_url="/docs",
            environment=settings.app_env,
        )

    return app


# Default ASGI application instance
app = create_app()
