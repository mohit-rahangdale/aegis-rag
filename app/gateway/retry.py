"""Centralized retry policy with exponential backoff and jitter."""

import asyncio
import random
from typing import Any, Callable, Coroutine, Optional, Set, Tuple, Type, TypeVar

from app.gateway.exceptions import (
    CircuitBreakerOpenException,
    InvalidRequestException,
    ProviderAuthenticationException,
    ProviderRateLimitException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    UnsupportedProviderException,
)
from app.gateway.logging import log_provider_failure

T = TypeVar("T")

# Non-retryable exceptions that fail immediately without consuming retries
NON_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ProviderAuthenticationException,
    CircuitBreakerOpenException,
    UnsupportedProviderException,
    InvalidRequestException,
)

# Retryable exception classes
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ProviderUnavailableException,
    ProviderTimeoutException,
    ProviderRateLimitException,
    ConnectionError,
    TimeoutError,
)


def calculate_backoff_delay(
    attempt: int,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay with jitter."""
    calculated = initial_delay * (backoff_factor ** (attempt - 1))
    bounded = min(calculated, max_delay)
    if jitter:
        # Full jitter between 0 and bounded
        return random.uniform(0.5 * bounded, bounded)
    return bounded


async def execute_with_retry(
    func: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
    provider: str = "unknown",
    model: str = "unknown",
    request_id: str = "unknown",
    on_failure: Optional[Callable[[Exception, int], None]] = None,
) -> T:
    """Execute asynchronous callable with exponential backoff retry.

    Only transient failures are retried; fatal authentication or invalid requests fail fast.
    """
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            return await func()
        except NON_RETRYABLE_EXCEPTIONS as exc:
            # Immediate fail fast
            log_provider_failure(
                provider=provider,
                model=model,
                error=exc,
                request_id=request_id,
                attempt=attempt,
                will_retry=False,
            )
            if on_failure:
                on_failure(exc, attempt)
            raise
        except Exception as exc:
            last_exception = exc
            will_retry = attempt < max_retries

            log_provider_failure(
                provider=provider,
                model=model,
                error=exc,
                request_id=request_id,
                attempt=attempt,
                will_retry=will_retry,
            )

            if on_failure:
                on_failure(exc, attempt)

            if will_retry:
                delay = calculate_backoff_delay(
                    attempt=attempt,
                    initial_delay=initial_delay,
                    backoff_factor=backoff_factor,
                    max_delay=max_delay,
                )
                await asyncio.sleep(delay)
            else:
                break

    if last_exception:
        raise last_exception

    raise ProviderUnavailableException(
        message=f"Execution failed after {max_retries} attempts without explicit exception",
        provider=provider,
        model=model,
    )
