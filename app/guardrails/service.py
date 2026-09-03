from typing import List, Tuple

from app.guardrails.fast_path import get_fast_path_response
from app.guardrails.grounding import verify_grounding
from app.guardrails.injection import detect_prompt_injection
from app.guardrails.models import GuardrailResult, GroundingResult
from app.guardrails.output import sanitize_output



class GuardrailsService:
    """Service layer enforcing safety boundaries and token-saving fast-path dialogues."""

    def __init__(self, grounding_threshold: float = 0.35) -> None:
        self.grounding_threshold = grounding_threshold

    def validate_input(self, user_query: str) -> GuardrailResult:
        """Validate user query against prompt injection and check for token-saving fast paths."""
        # 1. Injection & jailbreak defense
        injection_result = detect_prompt_injection(user_query)
        if not injection_result.is_safe:
            return injection_result

        # 2. Check for routine dialogue fast-path (saves LLM tokens)
        fast_path = get_fast_path_response(user_query)
        if fast_path:
            return GuardrailResult(
                is_safe=True,
                fast_path_response=fast_path,
            )

        return GuardrailResult(is_safe=True)

    def validate_grounding(self, generation: str, contexts: List[str]) -> GroundingResult:
        """Verify generation is backed by retrieved source passages."""
        return verify_grounding(
            generation=generation,
            contexts=contexts,
            min_overlap_threshold=self.grounding_threshold,
        )

    def validate_output(self, response_text: str) -> Tuple[str, GuardrailResult]:
        """Ensure model output adheres to safety policies, redacts PII, and blocks prompt leaks."""
        return sanitize_output(response_text)

