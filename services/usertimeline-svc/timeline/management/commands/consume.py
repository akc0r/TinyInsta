from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from tinyinsta.bus import Consumer, redis_dedupe_store
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
    TOPICS = [
        types.POST_CREATED,
        types.POST_DELETED,
        types.POST_REPOSTED,
        types.POST_UNREPOSTED,
    ]
    GROUP_ID = "usertimeline-svc"

    def handle(self, *args, **options):
        consumer = Consumer(
            topics=self.TOPICS,
            group_id=self.GROUP_ID,
            dedupe=redis_dedupe_store(self.GROUP_ID),
        )
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
        elif envelope.type == types.POST_REPOSTED:
            # A repost surfaces the original post on the reposter's profile grid.
            store.add_post(data["user_id"], data["post_id"], _epoch(data.get("created_at")))
        elif envelope.type == types.POST_UNREPOSTED:
            store.remove_post(data["user_id"], data["post_id"])
