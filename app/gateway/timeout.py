"""Centralized asynchronous timeout execution for LLM providers."""

import asyncio
from typing import Any, Coroutine, TypeVar

from app.gateway.exceptions import ProviderTimeoutException

T = TypeVar("T")


async def execute_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout_seconds: float,
    provider: str,
    model: str,
) -> T:
    """Execute an asynchronous coroutine with strict timeout enforcement.

    Raises:
        ProviderTimeoutException: If the coroutine does not complete within timeout_seconds.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise ProviderTimeoutException(
            message=f"Call to provider '{provider}' timed out after {timeout_seconds:.1f} seconds",
            provider=provider,
            model=model,
            details={"timeout_seconds": timeout_seconds},
        ) from exc
