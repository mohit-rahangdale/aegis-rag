"""Abstract base class interface for LLM Providers."""

from abc import ABC, abstractmethod
from typing import Optional

from app.gateway.models import GatewayRequest, GatewayResponse


class LLMProvider(ABC):
    """Abstract interface that all concrete LLM providers must implement.

    Providers are purely responsible for:
    1. Translating standard GatewayRequest into provider-specific SDK / API payloads
    2. Invoking the provider API
    3. Translating the response into standard GatewayResponse
    4. Mapping provider-specific errors into unified GatewayException subclasses

    Providers MUST NOT duplicate retry, timeout, or circuit breaking logic.
    Those concerns are strictly centralized in the LLMGateway orchestrator.
    """

    def __init__(self, name: str, default_model: str, api_key: Optional[str] = None) -> None:
        self.name = name
        self.default_model = default_model
        self.api_key = api_key

    @abstractmethod
    async def generate(self, request: GatewayRequest) -> GatewayResponse:
        """Execute a text generation or chat completion request.

        Args:
            request: Standardized GatewayRequest.

        Returns:
            GatewayResponse containing content, usage, cost, and metadata.

        Raises:
            GatewayException: Unified gateway exception on failure.
        """
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Probe the provider's health or credential validity.

        Returns:
            True if the provider is operational, False otherwise.
        """
        pass
