import logging
import time

from django.core.management.base import BaseCommand
from tinyinsta.bus import Producer

from posts import outbox

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Relay pending transactional-outbox events to the bus."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=1.0)
        parser.add_argument("--batch", type=int, default=100)

    def handle(self, *args, **options):
        producer = Producer()
        interval = options["interval"]
        batch = options["batch"]
        self.stdout.write("Outbox relay started")
        while True:
            published = self._drain(producer, batch)
            # Only sleep when idle; under load we keep draining back-to-back.
            if published == 0:
                time.sleep(interval)

    def _drain(self, producer: Producer, batch: int) -> int:
        pending = outbox.fetch_pending(batch)
        count = 0
        for entry in pending:
            try:
                # Re-publish the persisted event_id so a redelivery after a crash
                # dedupes downstream instead of duplicating the side effect.
                producer.publish(
                    entry["type"],
                    entry["data"],
                    key=entry.get("key"),
                    event_id=entry["_id"],
                )
                producer.flush()
                outbox.mark_published(entry["_id"])
                count += 1
            except Exception:  # noqa: BLE001 — leave pending, retry next pass
                logger.warning("outbox: publish failed for %s", entry["_id"], exc_info=True)
                break
        return count
