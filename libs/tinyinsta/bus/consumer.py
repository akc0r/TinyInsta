from __future__ import annotations

import logging
from typing import Callable, Iterable

from tinyinsta.bus.config import BusConfig
from tinyinsta.bus.idempotency import DedupeStore, InMemoryDedupeStore
from tinyinsta.events.envelope import Envelope
from tinyinsta.observability.context import set_correlation_id

logger = logging.getLogger(__name__)

Handler = Callable[[Envelope], None]


class Consumer:
    def __init__(
        self,
        topics: Iterable[str],
        group_id: str,
        *,
        config: BusConfig | None = None,
        dedupe: DedupeStore | None = None,
    ) -> None:
        self._topics = list(topics)
        self._group_id = group_id
        self._config = config or BusConfig.from_env(client_id=group_id)
        self._dedupe = dedupe or InMemoryDedupeStore()
        self._consumer = None
        self._running = False

    def _ensure(self):
        if self._consumer is None:
            from confluent_kafka import Consumer as _KafkaConsumer

            self._consumer = _KafkaConsumer(
                {
                    "bootstrap.servers": self._config.bootstrap_servers,
                    "group.id": self._group_id,
                    "auto.offset.reset": "earliest",
                    "enable.auto.commit": False,
                }
            )
            self._consumer.subscribe(self._topics)
        return self._consumer

    def run(self, handler: Handler) -> None:
        consumer = self._ensure()
        self._running = True
        try:
            while self._running:
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error("consumer.error", extra={"error": str(msg.error())})
                    continue
                envelope = Envelope.from_json(msg.value())
                # Re-bind the originating trace so this consumer's logs (and any
                # events it re-emits) correlate back to the triggering action.
                set_correlation_id(envelope.correlation_id)
                if self._dedupe.seen(envelope.event_id):
                    consumer.commit(msg)
                    continue
                try:
                    handler(envelope)
                except Exception:
                    logger.exception("consumer.handler_failed", extra={"event_id": envelope.event_id})
                    continue
                self._dedupe.mark(envelope.event_id)
                consumer.commit(msg)
        finally:
            consumer.close()

    def stop(self) -> None:
        self._running = False
