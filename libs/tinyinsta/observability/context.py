"""The ambient correlation id.

Stored in a :class:`contextvars.ContextVar` so it is implicitly available to
every log record produced while handling a request or a bus message, without
threading it through every function signature.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None) -> None:
    _correlation_id.set(value)
