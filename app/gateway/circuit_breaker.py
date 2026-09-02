"""Circuit breaker implementation for LLM provider resilience and fail-fast behavior."""

import time
from enum import Enum
from typing import Optional

from app.gateway.exceptions import CircuitBreakerOpenException
from app.gateway.logging import log_circuit_state_change


class CircuitState(str, Enum):
    """Operational states of the circuit breaker."""

    CLOSED = "CLOSED"        # Healthy: traffic allowed
    OPEN = "OPEN"            # Tripped: requests fail fast
    HALF_OPEN = "HALF_OPEN"  # Testing: limited requests allowed to probe recovery


class CircuitBreaker:
    """Per-provider circuit breaker protecting against cascading failures."""

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ) -> None:
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_failure_time: float = 0.0
        self.last_state_change: float = time.monotonic()

    @property
    def is_open(self) -> bool:
        """Check if circuit is currently open."""
        return self.state == CircuitState.OPEN

    def check_availability(self) -> None:
        """Verify provider availability.

        Raises:
            CircuitBreakerOpenException: If the circuit is OPEN and recovery timeout has not elapsed.
        """
        now = time.monotonic()

        if self.state == CircuitState.OPEN:
            elapsed = now - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self._transition_to(
                    CircuitState.HALF_OPEN,
                    reason=f"Recovery timeout ({self.recovery_timeout}s) elapsed; probing health",
                )
            else:
                remaining = self.recovery_timeout - elapsed
                raise CircuitBreakerOpenException(
                    message=(
                        f"Circuit breaker is OPEN for provider '{self.provider}'. "
                        f"Failing fast. Retry in {remaining:.1f}s"
                    ),
                    provider=self.provider,
                    details={"remaining_cooldown_seconds": round(remaining, 1)},
                )

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to(
                    CircuitState.CLOSED,
                    reason=f"{self.success_count} consecutive successful probes",
                )
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on stable operation
            self.failure_count = 0

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record an operation failure."""
        now = time.monotonic()
        self.last_failure_time = now

        if self.state == CircuitState.HALF_OPEN:
            # Single failure in HALF_OPEN immediately trips back to OPEN
            self._transition_to(
                CircuitState.OPEN,
                reason=f"Failed probe during recovery: {error}",
            )
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._transition_to(
                    CircuitState.OPEN,
                    reason=f"Reached {self.failure_count} consecutive failures: {error}",
                )

    def reset(self) -> None:
        """Manually force reset to CLOSED state."""
        self._transition_to(CircuitState.CLOSED, reason="Manual reset invoked")
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

    def _transition_to(self, new_state: CircuitState, reason: Optional[str] = None) -> None:
        """Internal helper to transition states and log the event."""
        old_state = self.state
        if old_state != new_state:
            self.state = new_state
            self.last_state_change = time.monotonic()
            log_circuit_state_change(
                provider=self.provider,
                old_state=old_state.value,
                new_state=new_state.value,
                reason=reason,
            )
