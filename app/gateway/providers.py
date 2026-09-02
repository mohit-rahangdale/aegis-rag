"""Concrete LLM Provider implementations for Gemini and Mistral."""

import time
from typing import Any, Dict, List, Optional

from app.gateway.base import LLMProvider
from app.gateway.exceptions import (
    ProviderAuthenticationException,
    ProviderRateLimitException,
    ProviderUnavailableException,
)
from app.gateway.models import (
    CostEstimate,
    GatewayRequest,
    GatewayResponse,
    Role,
    TokenUsage,
)
from app.gateway.usage import calculate_cost


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation using google.genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gemini-2.5-flash",
    ) -> None:
        super().__init__(name="gemini", default_model=default_model, api_key=api_key)
        self._client = None
        if self.api_key:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)

    async def is_healthy(self) -> bool:
        """Check if Gemini credentials are configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def generate(self, request: GatewayRequest) -> GatewayResponse:
        """Generate response via Google Gemini."""
        if not self.api_key:
            raise ProviderAuthenticationException(
                message="Gemini API key is not configured or is empty",
                provider=self.name,
            )

        model = request.model or self.default_model
        start_time = time.perf_counter()

        try:
            from google import genai
            from google.genai import types

            client = self._client or genai.Client(api_key=self.api_key)

            # Separate system instruction if present
            system_instructions: List[str] = []
            contents: List[types.Content] = []

            for msg in request.messages:
                if msg.role == Role.SYSTEM:
                    system_instructions.append(msg.content)
                else:
                    role = "model" if msg.role == Role.ASSISTANT else "user"
                    contents.append(
                        types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=msg.content)],
                        )
                    )

            config = types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                top_p=request.top_p,
                stop_sequences=request.stop_sequences if request.stop_sequences else None,
                system_instruction="\n".join(system_instructions) if system_instructions else None,
            )

            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            # Extract generated content
            content_text = response.text or ""

            # Extract usage
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            cost = calculate_cost(
                provider=self.name,
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )

            return GatewayResponse(
                content=content_text,
                provider=self.name,
                model=model,
                finish_reason="stop",
                usage=usage,
                cost=cost,
                latency_ms=round(latency_ms, 2),
                request_id=request.request_id,
            )

        except Exception as exc:
            err_str = str(exc).lower()
            if "api key" in err_str or "unauthenticated" in err_str or "permission_denied" in err_str or "401" in err_str or "403" in err_str:
                raise ProviderAuthenticationException(
                    message=f"Gemini authentication failed: {exc}",
                    provider=self.name,
                    model=model,
                ) from exc
            if "resource_exhausted" in err_str or "quota" in err_str or "429" in err_str:
                raise ProviderRateLimitException(
                    message=f"Gemini rate limit exceeded: {exc}",
                    provider=self.name,
                    model=model,
                ) from exc
            raise ProviderUnavailableException(
                message=f"Gemini service error: {exc}",
                provider=self.name,
                model=model,
            ) from exc


class MistralProvider(LLMProvider):
    """Mistral AI LLM provider implementation using mistralai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "mistral-small-latest",
    ) -> None:
        super().__init__(name="mistral", default_model=default_model, api_key=api_key)
        self._client = None
        if self.api_key:
            from mistralai.client import Mistral
            self._client = Mistral(api_key=self.api_key)

    async def is_healthy(self) -> bool:
        """Check if Mistral credentials are configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def generate(self, request: GatewayRequest) -> GatewayResponse:
        """Generate response via Mistral AI."""
        if not self.api_key:
            raise ProviderAuthenticationException(
                message="Mistral API key is not configured or is empty",
                provider=self.name,
            )

        model = request.model or self.default_model
        start_time = time.perf_counter()

        try:
            from mistralai.client import Mistral

            client = self._client or Mistral(api_key=self.api_key)

            messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.messages
            ]

            response = await client.chat.complete_async(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            choice = response.choices[0]
            content_text = choice.message.content or ""
            finish_reason = getattr(choice, "finish_reason", "stop") or "stop"

            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(response.usage, "completion_tokens", 0) or 0

            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            cost = calculate_cost(
                provider=self.name,
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )

            return GatewayResponse(
                content=content_text,
                provider=self.name,
                model=model,
                finish_reason=str(finish_reason),
                usage=usage,
                cost=cost,
                latency_ms=round(latency_ms, 2),
                request_id=request.request_id,
            )

        except Exception as exc:
            err_str = str(exc).lower()
            if "unauthorized" in err_str or "api key" in err_str or "401" in err_str or "403" in err_str:
                raise ProviderAuthenticationException(
                    message=f"Mistral authentication failed: {exc}",
                    provider=self.name,
                    model=model,
                ) from exc
            if "rate limit" in err_str or "quota" in err_str or "429" in err_str:
                raise ProviderRateLimitException(
                    message=f"Mistral rate limit exceeded: {exc}",
                    provider=self.name,
                    model=model,
                ) from exc
            raise ProviderUnavailableException(
                message=f"Mistral service error: {exc}",
                provider=self.name,
                model=model,
            ) from exc
