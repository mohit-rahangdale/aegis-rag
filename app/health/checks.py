"""Unified health checks across external storage dependencies."""

import asyncio
from typing import Dict, Tuple

from app.db.session import check_db_health
from app.storage.minio.client import check_minio_health
from app.storage.qdrant.client import check_qdrant_health
from app.storage.redis.client import check_redis_health


async def _probe_with_timeout(coro, timeout_seconds: float = 1.0) -> bool:
    """Run an async health probe with strict timeout."""
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        return result is True
    except Exception:
        return False


async def check_all_dependencies(timeout_seconds: float = 1.0) -> Dict[str, str]:
    """Check availability of PostgreSQL, Redis, MinIO, and Qdrant in parallel.

    Returns a clean mapping of service names to status strings ('healthy' or 'unreachable').
    Never exposes passwords, connection strings, or internal tracebacks.
    """
    results = await asyncio.gather(
        _probe_with_timeout(check_db_health(), timeout_seconds),
        _probe_with_timeout(check_redis_health(), timeout_seconds),
        _probe_with_timeout(check_minio_health(), timeout_seconds),
        _probe_with_timeout(check_qdrant_health(), timeout_seconds),
        return_exceptions=True,
    )

    postgres_ok, redis_ok, minio_ok, qdrant_ok = results

    return {
        "postgres": "healthy" if postgres_ok is True else "unreachable",
        "redis": "healthy" if redis_ok is True else "unreachable",
        "minio": "healthy" if minio_ok is True else "unreachable",
        "qdrant": "healthy" if qdrant_ok is True else "unreachable",
    }



def get_overall_status(dependencies: Dict[str, str]) -> str:
    """Derive aggregate system status from dependency statuses."""
    if all(status == "healthy" for status in dependencies.values()):
        return "healthy"
    if any(status == "healthy" for status in dependencies.values()):
        return "degraded"
    return "unhealthy"


async def get_overall_health() -> Tuple[str, Dict[str, str]]:
    """Return tuple of overall status and dependency map."""
    deps = await check_all_dependencies()
    status = get_overall_status(deps)
    return status, deps
