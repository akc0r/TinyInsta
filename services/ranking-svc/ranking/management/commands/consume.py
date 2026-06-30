from django.core.management.base import BaseCommand
from tinyinsta.bus import Consumer, redis_dedupe_store
from tinyinsta.events import Envelope, types

from ranking import store

# Engagement weights.
LIKE_WEIGHT = 1.0
COMMENT_WEIGHT = 2.0


class Command(BaseCommand):
    TOPICS = [
        types.POST_CREATED,
        types.POST_DELETED,
        types.POST_LIKED,
        types.POST_UNLIKED,
        types.POST_COMMENTED,
    ]
    GROUP_ID = "ranking-svc"

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
            types.POST_CREATED: self._on_created,
            types.POST_DELETED: self._on_deleted,
            types.POST_LIKED: self._on_liked,
            types.POST_UNLIKED: self._on_unliked,
            types.POST_COMMENTED: self._on_commented,
        }
        handlers[envelope.type](envelope.data)

    def _on_created(self, data: dict) -> None:
        store.record_post(
            data["post_id"], data["author_id"], data.get("created_at", ""), data.get("kind", "post")
        )

    def _on_deleted(self, data: dict) -> None:
        store.remove_post(data["post_id"])

    def _on_liked(self, data: dict) -> None:
        post_id = data["post_id"]
        store.add_engagement(post_id, LIKE_WEIGHT)
        store.bump_affinity(data["user_id"], store.author_of(post_id), LIKE_WEIGHT)

    def _on_unliked(self, data: dict) -> None:
        post_id = data["post_id"]
        store.add_engagement(post_id, -LIKE_WEIGHT)
        store.bump_affinity(data["user_id"], store.author_of(post_id), -LIKE_WEIGHT)

    def _on_commented(self, data: dict) -> None:
        post_id = data["post_id"]
        store.add_engagement(post_id, COMMENT_WEIGHT)
        store.bump_affinity(data["author_id"], data.get("post_author_id"), COMMENT_WEIGHT)
