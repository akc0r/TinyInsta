from __future__ import annotations

import os
from typing import Any

from tinyinsta.bus.config import BusConfig
from tinyinsta.events import registry
from tinyinsta.events.envelope import Envelope
from tinyinsta.observability.context import get_correlation_id, new_correlation_id


class Producer:
    def __init__(self, config: BusConfig | None = None, *, validate: bool | None = None) -> None:
        self._config = config or BusConfig.from_env()
        self._producer = None
        # Validate every payload against its registered contract before it goes
        # on the wire (catches a contract breach at the source). Off via
        # BUS_VALIDATE=0 for e.g. a deliberate malformed-event test.
        self._validate = (
            validate
            if validate is not None
            else os.environ.get("BUS_VALIDATE", "1") not in ("0", "false", "False")
        )

    def _ensure(self):
        if self._producer is None:
            from confluent_kafka import Producer as _KafkaProducer

            self._producer = _KafkaProducer(
                {
                    "bootstrap.servers": self._config.bootstrap_servers,
                    "client.id": self._config.client_id,
                    "enable.idempotence": True,
                }
            )
        return self._producer

    def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        *,
        key: str | None = None,
        version: int = 1,
        event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> Envelope:
        if self._validate:
            registry.validate(event_type, data)
        # Stamp the ambient trace (set by the HTTP middleware or an upstream
        # consumer) so the event stays correlated; mint one if published outside
        # any request context. `event_id`/`correlation_id` can be supplied so a
        # relay (e.g. the transactional outbox) re-publishes the *same* identity
        # it persisted — redeliveries then dedupe correctly downstream.
        envelope = Envelope(
            type=event_type,
            data=data,
            version=version,
            correlation_id=correlation_id or get_correlation_id() or new_correlation_id(),
        )
        if event_id is not None:
            envelope.event_id = event_id
        producer = self._ensure()
        producer.produce(
            topic=event_type,
            key=(key or envelope.event_id).encode("utf-8"),
            value=envelope.to_json(),
        )
        producer.poll(0)
        return envelope

    def flush(self, timeout: float = 5.0) -> None:
        if self._producer is not None:
            self._producer.flush(timeout)
