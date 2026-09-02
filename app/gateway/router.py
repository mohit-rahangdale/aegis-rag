"""Provider registration and routing resolution for LLM Gateway."""

from typing import Dict, List, Optional

from app.gateway.base import LLMProvider
from app.gateway.exceptions import UnsupportedProviderException


class ProviderRouter:
    """Manages registered LLM providers and determines invocation order."""

    def __init__(
        self,
        primary_provider: str = "gemini",
        fallback_provider: str = "mistral",
    ) -> None:
        self.primary_provider = primary_provider.lower()
        self.fallback_provider = fallback_provider.lower()
        self._providers: Dict[str, LLMProvider] = {}

    def register_provider(self, provider: LLMProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.name.lower()] = provider

    def get_provider(self, name: str) -> LLMProvider:
        """Retrieve a registered provider by name.

        Raises:
            UnsupportedProviderException: If the provider is not registered.
        """
        normalized = name.lower().strip()
        if normalized not in self._providers:
            available = list(self._providers.keys())
            raise UnsupportedProviderException(
                message=f"Provider '{normalized}' is not supported or registered. Available: {available}",
                provider=normalized,
                details={"available_providers": available},
            )
        return self._providers[normalized]

    def has_provider(self, name: str) -> bool:
        """Check whether a provider is registered."""
        return name.lower().strip() in self._providers

    def list_providers(self) -> List[str]:
        """List names of all registered providers."""
        return list(self._providers.keys())

    def resolve_provider_sequence(self, requested_provider: Optional[str] = None) -> List[str]:
        """Determine ordered list of providers to attempt for a request.

        If a specific provider is requested by the caller, it is attempted first.
        If it fails, the designated fallback provider is attempted (if different).
        """
        if requested_provider:
            primary = requested_provider.lower().strip()
            # If the requested provider is already the fallback, sequence is just [requested]
            if primary == self.fallback_provider:
                return [primary]
            # If the requested provider is registered, fallback to configured fallback
            return [primary, self.fallback_provider]

        # Default sequence: primary -> fallback
        sequence = [self.primary_provider]
        if self.fallback_provider != self.primary_provider:
            sequence.append(self.fallback_provider)
        return sequence
