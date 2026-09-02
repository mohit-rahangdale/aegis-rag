"""Structured logging configuration for AegisRAG.

Provides JSON and human-readable text formatters with contextual metadata.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config.settings import Settings, get_settings


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def __init__(self, service_name: str = "aegisrag", environment: str = "development"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
            "source": f"{record.filename}:{record.lineno}",
        }

        # Include request ID or tracing context if present on record
        if hasattr(record, "request_id"):
            log_payload["request_id"] = record.request_id

        # Include any extra metadata passed via extra dict
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "request_id",
        }
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }
        if extras:
            log_payload["extra"] = extras

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)


def setup_logging(settings: Optional[Settings] = None) -> None:
    """Configure root logging according to application settings."""
    if settings is None:
        settings = get_settings()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)

    if settings.log_format == "json":
        formatter = JSONFormatter(
            service_name=settings.app_name,
            environment=settings.app_env,
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Convenience helper to retrieve a named logger."""
    return logging.getLogger(name)
