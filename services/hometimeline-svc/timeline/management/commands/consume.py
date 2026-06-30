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
        types.USER_FOLLOWED,
        types.USER_UNFOLLOWED,
    ]
    GROUP_ID = "hometimeline-svc"

    def handle(self, *args, **options):
        consumer = Consumer(
            topics=self.TOPICS,
            group_id=self.GROUP_ID,
            dedupe=redis_dedupe_store(self.GROUP_ID),
        )
        self.stdout.write(f"Consuming {self.TOPICS} as group {self.GROUP_ID}")
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        handlers = {
            types.POST_CREATED: self._on_post_created,
            types.POST_DELETED: self._on_post_deleted,
            types.POST_REPOSTED: self._on_post_reposted,
            types.POST_UNREPOSTED: self._on_post_unreposted,
            types.USER_FOLLOWED: self._on_user_followed,
            types.USER_UNFOLLOWED: self._on_user_unfollowed,
        }
        handlers[envelope.type](envelope.data)

    def _on_post_created(self, data: dict) -> None:
        # Hybrid fan-out. For a celebrity (follower count over the threshold) we
        # do NOT fan out to followers — too expensive; their followers pull these
        # posts at read time (store.page). We still push to the author's own home
        # so they see their post immediately.
        author_id = data["author_id"]
        ts = _epoch(data.get("created_at"))
        if store.is_celebrity(author_id):
            store.mark_celebrity(author_id)
            store.fan_out([author_id], data["post_id"], ts)
            return
        targets = store.followers_of(author_id) + [author_id]
        store.fan_out(targets, data["post_id"], ts)

    def _on_post_deleted(self, data: dict) -> None:
        author_id = data["author_id"]
        targets = store.followers_of(author_id) + [author_id]
        store.remove_post(targets, data["post_id"])

    def _on_post_reposted(self, data: dict) -> None:
        # Fan the original post out to the reposter's followers (and the reposter).
        reposter = data["user_id"]
        ts = _epoch(data.get("created_at"))
        targets = store.followers_of(reposter) + [reposter]
        store.fan_out(targets, data["post_id"], ts)

    def _on_post_unreposted(self, data: dict) -> None:
        reposter = data["user_id"]
        targets = store.followers_of(reposter) + [reposter]
        store.remove_post(targets, data["post_id"])

    def _on_user_followed(self, data: dict) -> None:
        follower_id, followee_id = data["follower_id"], data["followee_id"]
        store.add_follower(followee_id, follower_id)
        store.add_following(follower_id, followee_id)
        # Promote to celebrity as soon as the follower count crosses the
        # threshold — independent of post/follow event ordering across topics.
        # A celebrity's posts aren't pushed, so back-fill would miss them; the
        # read-time pull (store.page) surfaces them instead.
        if store.is_celebrity(followee_id):
            store.mark_celebrity(followee_id)
        else:
            store.back_fill(follower_id, followee_id)

    def _on_user_unfollowed(self, data: dict) -> None:
        follower_id, followee_id = data["follower_id"], data["followee_id"]
        store.remove_follower(followee_id, follower_id)
        store.remove_following(follower_id, followee_id)
        # An account that drops back under the threshold returns to push fan-out.
        store.demote_if_below(followee_id)
        store.purge(follower_id, followee_id)
