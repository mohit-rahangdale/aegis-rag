"""Tests for the CircuitBreaker resilience pattern."""

import time
import pytest

from app.gateway.circuit_breaker import CircuitBreaker, CircuitState
from app.gateway.exceptions import CircuitBreakerOpenException


def test_circuit_breaker_initial_state():
    """Verify circuit breaker initializes in CLOSED state."""
    cb = CircuitBreaker(provider="gemini", failure_threshold=3, recovery_timeout=1.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.is_open is False
    # check_availability does not raise
    cb.check_availability()


def test_circuit_breaker_trips_to_open():
    """Verify circuit trips to OPEN after failure_threshold consecutive failures."""
    cb = CircuitBreaker(provider="gemini", failure_threshold=3, recovery_timeout=1.0)

    cb.record_failure(Exception("failure 1"))
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    cb.record_failure(Exception("failure 2"))
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 2

    cb.record_failure(Exception("failure 3"))
    assert cb.state == CircuitState.OPEN
    assert cb.is_open is True

    # When OPEN, check_availability must fail fast
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        cb.check_availability()
    assert "Circuit breaker is OPEN for provider 'gemini'" in str(exc_info.value)


def test_circuit_breaker_recovers_to_half_open_and_closed():
    """Verify circuit recovers through HALF_OPEN to CLOSED after recovery timeout."""
    # Use small recovery timeout for testing
    cb = CircuitBreaker(
        provider="gemini",
        failure_threshold=2,
        recovery_timeout=0.1,
        success_threshold=2,
    )

    cb.record_failure(Exception("err 1"))
    cb.record_failure(Exception("err 2"))
    assert cb.state == CircuitState.OPEN

    # Sleep past recovery timeout
    time.sleep(0.15)

    # Calling check_availability should transition to HALF_OPEN
    cb.check_availability()
    assert cb.state == CircuitState.HALF_OPEN

    # Record successes to recover
    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.success_count == 1

    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure_immediately_opens():
    """Verify single failure during HALF_OPEN immediately trips back to OPEN."""
    cb = CircuitBreaker(
        provider="gemini",
        failure_threshold=2,
        recovery_timeout=0.05,
        success_threshold=2,
    )

    cb.record_failure(Exception("err 1"))
    cb.record_failure(Exception("err 2"))
    assert cb.state == CircuitState.OPEN

    time.sleep(0.06)
    cb.check_availability()
    assert cb.state == CircuitState.HALF_OPEN

    # Failure during probing immediately returns to OPEN
    cb.record_failure(Exception("probe failed"))
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_manual_reset():
    """Verify manual reset returns circuit to CLOSED state."""
    cb = CircuitBreaker(provider="mistral", failure_threshold=2)
    cb.record_failure(Exception("err 1"))
    cb.record_failure(Exception("err 2"))
    assert cb.state == CircuitState.OPEN

    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
