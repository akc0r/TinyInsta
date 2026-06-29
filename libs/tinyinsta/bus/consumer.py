from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Callable, Iterable

from tinyinsta.bus.config import BusConfig
from tinyinsta.bus.idempotency import DedupeStore, InMemoryDedupeStore
from tinyinsta.events.envelope import Envelope
from tinyinsta.observability.context import set_correlation_id

logger = logging.getLogger(__name__)

Handler = Callable[[Envelope], None]

# Sentinel so `dlq_topic=None` can mean "disable the DLQ" (drop after retries)
# while the unset default routes to the per-group dead-letter topic.
_DEFAULT_DLQ = object()


class Consumer:
    def __init__(
        self,
        topics: Iterable[str],
        group_id: str,
        *,
        config: BusConfig | None = None,
        dedupe: DedupeStore | None = None,
        max_attempts: int | None = None,
        retry_backoff: float | None = None,
        dlq_topic: str | None = _DEFAULT_DLQ,  # type: ignore[assignment]
    ) -> None:
        self._topics = list(topics)
        self._group_id = group_id
        self._config = config or BusConfig.from_env(client_id=group_id)
        self._dedupe = dedupe or InMemoryDedupeStore()
        # Bounded in-process retry with exponential backoff before a message is
        # routed to the dead-letter queue. Kept short so a poison message can't
        # stall the partition past the consumer-group poll interval.
        self._max_attempts = (
            max_attempts
            if max_attempts is not None
            else int(os.environ.get("BUS_MAX_ATTEMPTS", "3"))
        )
        self._retry_backoff = (
            retry_backoff
            if retry_backoff is not None
            else float(os.environ.get("BUS_RETRY_BACKOFF", "0.5"))
        )
        # Default: one dead-letter topic per consumer group (dlq.<group_id>).
        # Pass dlq_topic=None to disable (exhausted messages are dropped+committed
        # instead of re-delivered forever).
        self._dlq_topic = (
            f"dlq.{group_id}" if dlq_topic is _DEFAULT_DLQ else dlq_topic
        )
        self._consumer = None
        self._dlq_producer = None
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
                outcome = self._deliver(handler, msg, envelope)
                if outcome == "ok":
                    # Mark as processed only on success: a dead-lettered message
                    # was not handled, so a deliberate replay should run again.
                    self._dedupe.mark(envelope.event_id)
                    consumer.commit(msg)
                elif outcome == "dead-lettered":
                    consumer.commit(msg)
                # "deferred": leave the offset uncommitted so the message is
                # re-delivered later (we could neither handle nor dead-letter it).
        finally:
            if self._dlq_producer is not None:
                self._dlq_producer.flush(5.0)
            consumer.close()

    def _deliver(self, handler: Handler, msg, envelope: Envelope) -> str:
        """Run the handler with bounded retry; dead-letter on exhaustion.

        Returns "ok" (handled), "dead-lettered" (routed to the DLQ or dropped),
        or "deferred" (could not handle and could not dead-letter → redeliver).
        """
        for attempt in range(1, self._max_attempts + 1):
            try:
                handler(envelope)
                return "ok"
            except Exception:
                if attempt < self._max_attempts:
                    backoff = self._retry_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "consumer.retry",
                        extra={
                            "event_id": envelope.event_id,
                            "attempt": attempt,
                            "max_attempts": self._max_attempts,
                            "backoff": backoff,
                        },
                    )
                    time.sleep(backoff)
                else:
                    logger.exception(
                        "consumer.handler_failed",
                        extra={
                            "event_id": envelope.event_id,
                            "attempts": self._max_attempts,
                        },
                    )
        return self._dead_letter(msg, envelope)

    def _dead_letter(self, msg, envelope: Envelope) -> str:
        if not self._dlq_topic:
            # DLQ disabled: drop the poison message (commit) rather than spin on
            # it forever. The failure was already logged at exception level.
            logger.error(
                "consumer.dropped",
                extra={"event_id": envelope.event_id, "reason": "dlq_disabled"},
            )
            return "dead-lettered"
        try:
            producer = self._dlq()
            producer.produce(
                topic=self._dlq_topic,
                key=msg.key(),
                value=msg.value(),  # original bytes, untouched, so it can be replayed
                headers=[
                    ("x-dlq-reason", b"handler_failed"),
                    ("x-dlq-source-topic", (msg.topic() or "").encode("utf-8")),
                    ("x-dlq-group", self._group_id.encode("utf-8")),
                    ("x-dlq-event-id", envelope.event_id.encode("utf-8")),
                    ("x-dlq-failed-at", _now_iso().encode("utf-8")),
                ],
            )
            producer.flush(5.0)
            logger.error(
                "consumer.dead_lettered",
                extra={"event_id": envelope.event_id, "dlq_topic": self._dlq_topic},
            )
            return "dead-lettered"
        except Exception:
            # Couldn't reach the DLQ: don't commit, so the message is redelivered
            # rather than silently lost.
            logger.exception(
                "consumer.dlq_publish_failed", extra={"event_id": envelope.event_id}
            )
            return "deferred"

    def _dlq(self):
        if self._dlq_producer is None:
            from confluent_kafka import Producer as _KafkaProducer

            self._dlq_producer = _KafkaProducer(
                {
                    "bootstrap.servers": self._config.bootstrap_servers,
                    "client.id": f"{self._group_id}-dlq",
                    "enable.idempotence": True,
                }
            )
        return self._dlq_producer

    def stop(self) -> None:
        self._running = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
