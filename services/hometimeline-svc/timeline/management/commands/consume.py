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
    TOPICS = [
        types.POST_CREATED,
        types.POST_DELETED,
        types.USER_FOLLOWED,
        types.USER_UNFOLLOWED,
    ]
    GROUP_ID = "hometimeline-svc"

    def handle(self, *args, **options):
        consumer = Consumer(topics=self.TOPICS, group_id=self.GROUP_ID)
        self.stdout.write(f"Consuming {self.TOPICS} as group {self.GROUP_ID}")
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        handlers = {
            types.POST_CREATED: self._on_post_created,
            types.POST_DELETED: self._on_post_deleted,
            types.USER_FOLLOWED: self._on_user_followed,
            types.USER_UNFOLLOWED: self._on_user_unfollowed,
        }
        handlers[envelope.type](envelope.data)

    def _on_post_created(self, data: dict) -> None:
        # Fan-out on write: push the post to every follower's home timeline, and
        # to the author's own so they see it immediately after posting.
        author_id = data["author_id"]
        targets = store.followers_of(author_id) + [author_id]
        store.fan_out(targets, data["post_id"], _epoch(data.get("created_at")))

    def _on_post_deleted(self, data: dict) -> None:
        author_id = data["author_id"]
        targets = store.followers_of(author_id) + [author_id]
        store.remove_post(targets, data["post_id"])

    def _on_user_followed(self, data: dict) -> None:
        follower_id, followee_id = data["follower_id"], data["followee_id"]
        store.add_follower(followee_id, follower_id)
        store.back_fill(follower_id, followee_id)

    def _on_user_unfollowed(self, data: dict) -> None:
        follower_id, followee_id = data["follower_id"], data["followee_id"]
        store.remove_follower(followee_id, follower_id)
        store.purge(follower_id, followee_id)
