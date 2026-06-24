from django.core.management.base import BaseCommand

from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types


class Command(BaseCommand):
    TOPICS = [types.USER_CREATED, types.POST_CREATED, types.POST_DELETED]
    GROUP_ID = "search-svc"

    def handle(self, *args, **options):
        consumer = Consumer(topics=self.TOPICS, group_id=self.GROUP_ID)
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        if envelope.type == types.USER_CREATED:
            raise NotImplementedError  # TODO: index.index_user(...)
        if envelope.type == types.POST_CREATED:
            raise NotImplementedError  # TODO: index.index_post(...)
        if envelope.type == types.POST_DELETED:
            raise NotImplementedError  # TODO: index.remove_post(...)
