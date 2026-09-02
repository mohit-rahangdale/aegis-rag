"""Production-grade LLM Gateway module for AegisRAG."""

from app.gateway.base import LLMProvider
from app.gateway.circuit_breaker import CircuitBreaker, CircuitState
from app.gateway.exceptions import (
    AllProvidersFailedException,
    CircuitBreakerOpenException,
    GatewayException,
    InvalidRequestException,
    ProviderAuthenticationException,
    ProviderRateLimitException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    UnsupportedProviderException,
)
from app.gateway.models import (
    ChatMessage,
    CostEstimate,
    GatewayRequest,
    GatewayResponse,
    Role,
    TokenUsage,
)
from app.gateway.providers import GeminiProvider, MistralProvider
from app.gateway.router import ProviderRouter
from app.gateway.service import LLMGateway
from app.gateway.usage import calculate_cost

__all__ = [
    "LLMGateway",
    "LLMProvider",
    "GeminiProvider",
    "MistralProvider",
    "ProviderRouter",
    "CircuitBreaker",
    "CircuitState",
    "GatewayRequest",
    "GatewayResponse",
    "ChatMessage",
    "Role",
    "TokenUsage",
    "CostEstimate",
    "calculate_cost",
    "GatewayException",
    "ProviderUnavailableException",
    "ProviderTimeoutException",
    "ProviderRateLimitException",
    "ProviderAuthenticationException",
    "CircuitBreakerOpenException",
    "AllProvidersFailedException",
    "UnsupportedProviderException",
    "InvalidRequestException",
]
