from __future__ import annotations

from typing import Any

from tinyinsta.bus.config import BusConfig
from tinyinsta.events.envelope import Envelope


class Producer:
    def __init__(self, config: BusConfig | None = None) -> None:
        self._config = config or BusConfig.from_env()
        self._producer = None

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
    ) -> Envelope:
        envelope = Envelope(type=event_type, data=data, version=version)
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
