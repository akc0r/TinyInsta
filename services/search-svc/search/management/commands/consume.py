from django.core.management.base import BaseCommand
from tinyinsta.bus import Consumer, redis_dedupe_store
from tinyinsta.events import Envelope, types

from search import index


class Command(BaseCommand):
    TOPICS = [types.USER_CREATED, types.POST_CREATED, types.POST_DELETED]
    GROUP_ID = "search-svc"

    def handle(self, *args, **options):
        index.ensure_indices()
        consumer = Consumer(
            topics=self.TOPICS,
            group_id=self.GROUP_ID,
            dedupe=redis_dedupe_store(self.GROUP_ID),
        )
        self.stdout.write(f"Consuming {self.TOPICS} as group {self.GROUP_ID}")
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        data = envelope.data
        if envelope.type == types.USER_CREATED:
            index.index_user(data["user_id"], data["username"], data.get("bio", ""))
        elif envelope.type == types.POST_CREATED:
            index.index_post(data)
        elif envelope.type == types.POST_DELETED:
            index.remove_post(data["post_id"])
