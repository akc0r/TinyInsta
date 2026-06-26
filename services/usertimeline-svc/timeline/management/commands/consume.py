from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types

from timeline import store


def _epoch(value) -> float:
    """Turn an event timestamp into a numeric ZSET score (epoch seconds)."""
    if value is None:
        return datetime.now(timezone.utc).timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(value).timestamp()


class Command(BaseCommand):
    TOPICS = [types.POST_CREATED, types.POST_DELETED]
    GROUP_ID = "usertimeline-svc"

    def handle(self, *args, **options):
        consumer = Consumer(topics=self.TOPICS, group_id=self.GROUP_ID)
        self.stdout.write(f"Consuming {self.TOPICS} as group {self.GROUP_ID}")
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        data = envelope.data
        if envelope.type == types.POST_CREATED:
            store.add_post(
                data["author_id"], data["post_id"], _epoch(data.get("created_at"))
            )
        elif envelope.type == types.POST_DELETED:
            store.remove_post(data["author_id"], data["post_id"])
