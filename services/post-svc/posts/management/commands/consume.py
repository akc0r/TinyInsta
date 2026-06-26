from django.core.management.base import BaseCommand
from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types

from posts.mongo import posts_collection


class Command(BaseCommand):
    TOPICS = [types.MEDIA_PROCESSED]
    GROUP_ID = "post-svc"

    def handle(self, *args, **options):
        consumer = Consumer(topics=self.TOPICS, group_id=self.GROUP_ID)
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        if envelope.type == types.MEDIA_PROCESSED:
            self._attach_variants(envelope.data)

    @staticmethod
    def _attach_variants(data: dict) -> None:
        """Cache the variants on any post that already references this media so a
        single post read carries the renderable URLs without a media-svc hop.

        Idempotent: a `$set` keyed by media_id, safe to replay. Posts created
        after this event still resolve variants via GET /media/{id}.
        """
        media_id = data["media_id"]
        variants = data.get("variants", {})
        posts_collection().update_many(
            {"media_ids": media_id},
            {"$set": {f"media_variants.{media_id}": variants}},
        )
