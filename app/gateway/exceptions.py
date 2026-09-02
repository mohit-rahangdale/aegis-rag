"""Unified exception hierarchy for the LLM Gateway."""

from typing import Any, Dict, Optional


class GatewayException(Exception):
    """Base exception for all LLM Gateway errors."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model
        self.details = details or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.append(f"provider={self.provider}")
        if self.model:
            parts.append(f"model={self.model}")
        return " | ".join(parts)


class ProviderUnavailableException(GatewayException):
    """Raised when an LLM provider endpoint is unreachable or returns 5xx."""


class ProviderTimeoutException(GatewayException):
    """Raised when an LLM provider call exceeds the configured timeout."""


class ProviderRateLimitException(GatewayException):
    """Raised when an LLM provider returns a 429 Too Many Requests."""


class ProviderAuthenticationException(GatewayException):
    """Raised when provider API credentials are missing, invalid, or unauthorized."""


class CircuitBreakerOpenException(GatewayException):
    """Raised when a request is blocked because the provider's circuit breaker is OPEN."""


class AllProvidersFailedException(GatewayException):
    """Raised when all configured providers (primary and fallbacks) fail."""

    def __init__(
        self,
        message: str = "All configured LLM providers failed to fulfill request",
        attempted_providers: Optional[list[str]] = None,
        errors: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            message=message,
            details={"attempted_providers": attempted_providers or [], "errors": errors or {}},
        )
        self.attempted_providers = attempted_providers or []
        self.errors = errors or {}


class UnsupportedProviderException(GatewayException):
    """Raised when a requested provider is not supported or not registered."""


class InvalidRequestException(GatewayException):
    """Raised when a request payload fails gateway-level validation."""
