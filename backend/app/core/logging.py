"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars
from structlog.typing import EventDict, Processor


def _add_log_level_upper(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Ensure log level is uppercase for consistency."""
    event_dict["level"] = event_dict.get("level", method).upper()
    return event_dict


def _drop_color_message_key(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Remove uvicorn's color_message key which duplicates 'message'."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(log_level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog for the application.

    In production (json_output=True):
        - Renders as JSON (suitable for log aggregation pipelines)
    In development (json_output=False):
        - Renders with coloured ConsoleRenderer for human readability

    Args:
        log_level: Standard Python log level string (DEBUG, INFO, etc.).
        json_output: When True, emit JSON lines; otherwise use ConsoleRenderer.
    """
    log_level_int = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        merge_contextvars,
        structlog.stdlib.add_logger_name,
        _add_log_level_upper,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _drop_color_message_key,
    ]

    if json_output:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level_int),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level_int)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.get_logger(__name__).info(
        "logging configured",
        level=log_level,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Context helpers – re-exported so callers don't need to import structlog
# ---------------------------------------------------------------------------
def bind_request_context(
    request_id: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Bind per-request context variables for inclusion in every log line."""
    clear_contextvars()
    ctx: dict[str, str] = {"request_id": request_id}
    if user_id is not None:
        ctx["user_id"] = user_id
    if tenant_id is not None:
        ctx["tenant_id"] = tenant_id
    bind_contextvars(**ctx)


def clear_request_context() -> None:
    """Clear per-request context variables (call in response cleanup)."""
    clear_contextvars()


__all__ = [
    "configure_logging",
    "bind_request_context",
    "clear_request_context",
]
