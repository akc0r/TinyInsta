from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand

from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types


class Command(BaseCommand):
    TOPICS = [
        types.POST_LIKED,
        types.POST_UNLIKED,
        types.POST_COMMENTED,
        types.STORY_CREATED,
        types.USER_FOLLOWED,
    ]
    GROUP_ID = "realtime-svc"

    def handle(self, *args, **options):
        self.layer = get_channel_layer()
        consumer = Consumer(topics=self.TOPICS, group_id=self.GROUP_ID)
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        # TODO: route to group user:{id} / post:{id} via self.layer, persist Notification
        raise NotImplementedError
