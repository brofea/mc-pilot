"""Structured logging configuration with a small stable schema."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Final

_STANDARD_RECORD_FIELDS: Final[frozenset[str]] = frozenset(
    logging.makeLogRecord({}).__dict__
)


class JsonFormatter(logging.Formatter):
    """Render log records as one-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "component": record.name,
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    """Configure the root logger once for application startup."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
