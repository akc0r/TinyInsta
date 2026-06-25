from django.core.management.base import BaseCommand

from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types

from stories import store


class Command(BaseCommand):
    # The story bar shows the active stories of accounts the viewer follows, and
    # close-friends stories only to the author's close-friends set. stories-svc
    # keeps local projections of both graphs, built from the user.* events —
    # never reading user-svc's database.
    TOPICS = [
        types.USER_FOLLOWED,
        types.USER_UNFOLLOWED,
        types.USER_CLOSE_FRIEND_ADDED,
        types.USER_CLOSE_FRIEND_REMOVED,
    ]
    GROUP_ID = "stories-svc"

    def handle(self, *args, **options):
        consumer = Consumer(topics=self.TOPICS, group_id=self.GROUP_ID)
        self.stdout.write(f"Consuming {self.TOPICS} as group {self.GROUP_ID}")
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        handlers = {
            types.USER_FOLLOWED: self._on_followed,
            types.USER_UNFOLLOWED: self._on_unfollowed,
            types.USER_CLOSE_FRIEND_ADDED: self._on_close_added,
            types.USER_CLOSE_FRIEND_REMOVED: self._on_close_removed,
        }
        handlers[envelope.type](envelope.data)

    def _on_followed(self, data: dict) -> None:
        store.add_following(data["follower_id"], data["followee_id"])

    def _on_unfollowed(self, data: dict) -> None:
        store.remove_following(data["follower_id"], data["followee_id"])

    def _on_close_added(self, data: dict) -> None:
        store.add_close_friend(data["owner_id"], data["friend_id"])

    def _on_close_removed(self, data: dict) -> None:
        store.remove_close_friend(data["owner_id"], data["friend_id"])
