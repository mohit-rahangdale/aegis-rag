"""Tests for centralized retry and timeout mechanics."""

import asyncio
import pytest

from app.gateway.exceptions import (
    ProviderAuthenticationException,
    ProviderTimeoutException,
    ProviderUnavailableException,
)
from app.gateway.retry import execute_with_retry
from app.gateway.timeout import execute_with_timeout


@pytest.mark.anyio
async def test_timeout_success():
    """Verify execution completes within timeout."""
    async def fast_coro():
        return "completed"

    result = await execute_with_timeout(
        coro=fast_coro(),
        timeout_seconds=1.0,
        provider="gemini",
        model="gemini-2.5-flash",
    )
    assert result == "completed"


@pytest.mark.anyio
async def test_timeout_triggers_exception():
    """Verify execution exceeding timeout raises ProviderTimeoutException."""
    async def slow_coro():
        await asyncio.sleep(0.5)
        return "too late"

    with pytest.raises(ProviderTimeoutException) as exc_info:
        await execute_with_timeout(
            coro=slow_coro(),
            timeout_seconds=0.05,
            provider="gemini",
            model="gemini-2.5-flash",
        )

    err = exc_info.value
    assert err.provider == "gemini"
    assert "timed out after 0.1 seconds" in str(err) or "timed out" in str(err)


@pytest.mark.anyio
async def test_retry_eventual_success():
    """Verify retry recovers after transient failures."""
    call_count = 0

    async def flaky_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ProviderUnavailableException(message="Temporary 503", provider="gemini")
        return "success"

    result = await execute_with_retry(
        func=flaky_call,
        max_retries=3,
        initial_delay=0.01,
        backoff_factor=1.5,
        provider="gemini",
        model="gemini-2.5-flash",
    )
    assert result == "success"
    assert call_count == 3


@pytest.mark.anyio
async def test_retry_exhaustion_raises():
    """Verify retry raises final exception when max_retries is reached."""
    call_count = 0

    async def always_failing():
        nonlocal call_count
        call_count += 1
        raise ProviderUnavailableException(message="Persistent 500", provider="gemini")

    with pytest.raises(ProviderUnavailableException):
        await execute_with_retry(
            func=always_failing,
            max_retries=2,
            initial_delay=0.01,
            backoff_factor=1.5,
            provider="gemini",
            model="gemini-2.5-flash",
        )
    assert call_count == 2


@pytest.mark.anyio
async def test_retry_does_not_retry_auth_failure():
    """Verify non-retryable authentication failure fails fast on attempt 1."""
    call_count = 0

    async def auth_failing():
        nonlocal call_count
        call_count += 1
        raise ProviderAuthenticationException(message="Invalid API Key", provider="gemini")

    with pytest.raises(ProviderAuthenticationException):
        await execute_with_retry(
            func=auth_failing,
            max_retries=3,
            initial_delay=0.01,
            provider="gemini",
            model="gemini-2.5-flash",
        )
    # Must not retry
    assert call_count == 1
