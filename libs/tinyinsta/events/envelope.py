from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Envelope:
    type: str
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(default_factory=_now_iso)
    version: int = 1
    # Carries the originating request's trace across the bus so consumers' logs
    # (and any events they re-emit) stitch back to the action that triggered them.
    correlation_id: str | None = None

    def to_json(self) -> bytes:
        return json.dumps(
            {
                "event_id": self.event_id,
                "type": self.type,
                "occurred_at": self.occurred_at,
                "version": self.version,
                "correlation_id": self.correlation_id,
                "data": self.data,
            }
        ).encode("utf-8")

    @classmethod
    def from_json(cls, raw: bytes | str) -> "Envelope":
        obj = json.loads(raw)
        return cls(
            type=obj["type"],
            data=obj["data"],
            event_id=obj["event_id"],
            occurred_at=obj["occurred_at"],
            version=obj.get("version", 1),
            correlation_id=obj.get("correlation_id"),
        )
