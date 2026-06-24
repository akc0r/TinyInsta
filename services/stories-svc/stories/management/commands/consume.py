from django.core.management.base import BaseCommand

from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types


class Command(BaseCommand):
    TOPICS = [types.MEDIA_PROCESSED]
    GROUP_ID = "stories-svc"

    def handle(self, *args, **options):
        consumer = Consumer(topics=self.TOPICS, group_id=self.GROUP_ID)
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        if envelope.type == types.MEDIA_PROCESSED:
            raise NotImplementedError  # TODO: attach variants to the story
