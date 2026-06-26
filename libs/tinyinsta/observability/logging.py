"""Structured-logging building blocks wired up by the service settings base.

- :class:`ContextFilter` stamps every record with ``service`` and the ambient
  ``correlation_id`` (see :mod:`tinyinsta.observability.context`).
- ``JSON_LOGGING`` is a ready-made ``LOGGING`` dict the settings base installs so
  all logs are one JSON object per line — directly ingestible by Filebeat → ES.
"""

from __future__ import annotations

import logging
import os

from tinyinsta.observability.context import get_correlation_id


class ContextFilter(logging.Filter):
    """Inject ``service`` and ``correlation_id`` onto every record."""

    def __init__(self, service: str | None = None) -> None:
        super().__init__()
        self._service = service or os.environ.get("SERVICE_NAME", "tinyinsta-svc")

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self._service
        record.correlation_id = get_correlation_id() or "-"
        return True


def build_logging(level: str) -> dict:
    """A ``LOGGING`` config emitting one JSON object per line.

    Uses ``python-json-logger`` so any ``extra={...}`` a log call passes lands as
    top-level JSON fields alongside ``service`` and ``correlation_id``.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"context": {"()": "tinyinsta.observability.logging.ContextFilter"}},
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(service)s "
                "%(correlation_id)s %(message)s",
                "rename_fields": {
                    "asctime": "timestamp",
                    "levelname": "level",
                    "name": "logger",
                },
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["context"],
            }
        },
        "root": {"handlers": ["console"], "level": level},
    }
