from django.core.management.base import BaseCommand

from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types


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
        raise NotImplementedError

    def _on_post_deleted(self, data: dict) -> None:
        raise NotImplementedError

    def _on_user_followed(self, data: dict) -> None:
        raise NotImplementedError

    def _on_user_unfollowed(self, data: dict) -> None:
        raise NotImplementedError
