"""Structured logging for CrumbBob.

Provides JSON-formatted logs suitable for ingestion into log aggregators
(Datadog, Loki, CloudWatch, etc.) with per-request correlation IDs.

Usage:
    from crumdbob.logging_config import configure_logging, request_id_ctx

    configure_logging(level="INFO", json_output=True)
    logger = logging.getLogger(__name__)

    # Inside a request handler:
    request_id_ctx.set("req-abc123")
    logger.info("processing", extra={"user_id": 42})
    # → {"ts": "...", "level": "INFO", "request_id": "req-abc123",
    #    "logger": "...", "msg": "processing", "user_id": 42}
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Context variable bound per-request so log records inherit the request ID
# without callers having to pass it through every function signature.
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "crumdbob_request_id", default=None
)

# Reserved LogRecord attributes — we serialize everything else as "extra".
_RESERVED_LOG_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    The output is one record per line so it can be `tail | jq`'d in a shell
    or shipped to a log aggregator without further parsing. Timestamps are
    UTC ISO-8601 with Z suffix for unambiguous machine parsing.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = request_id_ctx.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Pull anything passed via `logger.info("...", extra={...})` into the
        # JSON record so callers can attach structured context.
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_ATTRS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """Human-friendly fallback for interactive terminals."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-7s %(name)s [%(request_id)s] %(message)s",
            datefmt="%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_ctx.get() or "-"
        return super().format(record)


def configure_logging(
    level: str | int = "INFO",
    json_output: bool | None = None,
    stream: Any = None,
) -> None:
    """Configure the root logger with the given level and formatter.

    Args:
        level: Logging level name or numeric value.
        json_output: If True, emit JSON; if False, emit plain. When None
            (default), decide based on whether stdout is a TTY (interactive
            → plain) or piped (likely a log shipper → JSON). Override via
            the CRUMDBOB_LOG_FORMAT env var: "json" or "plain".
        stream: Stream to write logs to (defaults to stderr).
    """
    if json_output is None:
        env_override = os.getenv("CRUMDBOB_LOG_FORMAT", "").lower()
        if env_override in {"json", "plain"}:
            json_output = env_override == "json"
        else:
            json_output = not sys.stderr.isatty()

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter() if json_output else PlainFormatter())

    root = logging.getLogger()
    # Replace any existing handlers so reconfiguration is idempotent.
    root.handlers = [handler]
    root.setLevel(level)

    # Quiet down noisy third-party loggers at INFO so our own signal isn't drowned.
    for noisy in ("uvicorn.access", "watchdog", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
