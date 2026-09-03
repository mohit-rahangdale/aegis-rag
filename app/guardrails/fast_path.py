"""Fast-path dialogue handler for routine conversational messages.

Answers greetings, thanks, acknowledgments, and basic help without making
expensive retrieval or LLM calls, saving tokens and reducing latency.
"""

import re
from typing import Optional

_GREETING_PATTERN = re.compile(
    r"^(hi|hello|hey|greetings|howdy|good\s+(morning|afternoon|evening|day))[!.,\s]*$",
    re.IGNORECASE,
)
_THANKS_PATTERN = re.compile(
    r"^(thanks|thank\s+you|thank\s+you\s+so\s+much|thanks\s+a\s+lot|much\s+appreciated)[!.,\s]*$",
    re.IGNORECASE,
)
_FAREWELL_PATTERN = re.compile(
    r"^(bye|goodbye|see\s+you|see\s+ya|cya|take\s+care)[!.,\s]*$",
    re.IGNORECASE,
)
_ACK_PATTERN = re.compile(
    r"^(ok|okay|cool|got\s+it|understood|sure|fine|great)[!.,\s]*$",
    re.IGNORECASE,
)
_IDENTITY_PATTERN = re.compile(
    r"^(who\s+are\s+you|what\s+are\s+you|what\s+can\s+you\s+do|help|help\s+me)[?!.,\s]*$",
    re.IGNORECASE,
)


def get_fast_path_response(query: str) -> Optional[str]:
    """Return a canned response for routine conversational pleasantries.

    Returns None if the query contains real questions to allow normal retrieval.
    """
    text = query.strip()
    if not text:
        return None

    if _GREETING_PATTERN.match(text):
        return "Hello! How can I help you today? Feel free to ask questions about your documents."

    if _THANKS_PATTERN.match(text):
        return "You're welcome! Let me know if you need help with anything else."

    if _FAREWELL_PATTERN.match(text):
        return "Goodbye! Have a great day."

    if _ACK_PATTERN.match(text):
        return "Understood. Let me know when you have a question."

    if _IDENTITY_PATTERN.match(text):
        return (
            "I am AegisRAG, a document assistant. You can upload files (PDF, Markdown, text) "
            "and ask questions. I retrieve relevant sections and provide grounded answers."
        )

    return None
