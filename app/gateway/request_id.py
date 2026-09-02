"""Request correlation ID management using ContextVars."""

import uuid
from contextvars import ContextVar
from typing import Optional

_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_current_request_id() -> Optional[str]:
    """Retrieve current request ID from context."""
    return _request_id_ctx_var.get()


def set_current_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    _request_id_ctx_var.set(request_id)


def ensure_request_id(provided_id: Optional[str] = None) -> str:
    """Return existing ID, set provided ID, or generate a fresh UUID4."""
    if provided_id:
        set_current_request_id(provided_id)
        return provided_id

    current = get_current_request_id()
    if current:
        return current

    new_id = str(uuid.uuid4())
    set_current_request_id(new_id)
    return new_id
