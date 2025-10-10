"""Structured logging utilities for the DivineHaven backend."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter emitting structured log lines."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        """Format the log record as a JSON payload."""

        base: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)

        # Include any extra structured attributes that were passed via logger.bind
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                continue
            base.setdefault("extra", {})[key] = value

        return json.dumps(base, default=_json_default)


def _json_default(value: Any) -> Any:
    """Fallback JSON serializer for unsupported types."""

    if isinstance(value, (datetime,)):
        return value.isoformat()
    return str(value)


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured logging."""

    logging_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    logging.basicConfig(level=logging_level, handlers=[handler], force=True)


def get_logger(name: str = "divinehaven") -> logging.Logger:
    """Return a structured logger instance."""

    return logging.getLogger(name)
