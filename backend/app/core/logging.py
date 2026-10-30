"""
Structured Logging Configuration
==================================
Uses Python's standard logging module with a JSON formatter for production
and a human-readable formatter for development.
All log records include a request_id field (populated by middleware in Stage 2+).
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable for per-request IDs (set by middleware in Stage 2)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(""),
        }

        # Include extra fields passed via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in {
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
                "message",
            }:
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class DevFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    LEVEL_COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelname, "")
        rid = request_id_var.get("")
        rid_str = f" [{rid[:8]}]" if rid else ""
        prefix = f"{color}{record.levelname:8}{self.RESET}"
        return f"{prefix} {record.name}{rid_str}: {record.getMessage()}"


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger.
    - Production: JSON formatter to stdout (for log aggregators)
    - Development/test: human-readable colored formatter
    """
    from app.core.config import settings

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Use: logger = get_logger(__name__)."""
    return logging.getLogger(name)


def generate_request_id() -> str:
    """Generate a short request ID."""
    return uuid.uuid4().hex[:12]
