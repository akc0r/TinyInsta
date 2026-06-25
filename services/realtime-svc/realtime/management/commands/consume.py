from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand

from tinyinsta.bus import Consumer
from tinyinsta.events import Envelope, types

from realtime.consumers import post_group, user_group
from realtime.models import Notification


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
        self.stdout.write(f"Consuming {self.TOPICS} as group {self.GROUP_ID}")
        consumer.run(self._dispatch)

    def _dispatch(self, envelope: Envelope) -> None:
        handlers = {
            types.POST_LIKED: self._on_like,
            types.POST_UNLIKED: self._on_like,
            types.POST_COMMENTED: self._on_comment,
            types.USER_FOLLOWED: self._on_follow,
            types.STORY_CREATED: self._on_story,
        }
        handlers[envelope.type](envelope.data)

    # --- bus → channel layer -------------------------------------------------
    def _send(self, group: str, msg_type: str, data: dict) -> None:
        # msg_type "post.liked" → consumer handler post_liked (dots become _).
        async_to_sync(self.layer.group_send)(group, {"type": msg_type, "data": data})

    def _notify(self, user_id: str, ntype: str, payload: dict) -> None:
        # Persist (notification center) and push live to the recipient's group.
        note = Notification.objects.create(user_id=user_id, type=ntype, payload=payload)
        self._send(
            user_group(user_id),
            "notification",
            {
                "id": str(note.id),
                "notification_type": ntype,
                "payload": payload,
                "read": False,
                "created_at": note.created_at.isoformat(),
            },
        )

    # --- handlers ------------------------------------------------------------
    def _on_like(self, data: dict) -> None:
        # The event carries new_count → push the counter directly, no DB read.
        # Like notifications would need the post owner, which the event doesn't
        # carry (interaction-svc can't read post-svc), so likes are live-counter
        # only — see docs/realtime-svc.md.
        self._send(
            post_group(data["post_id"]),
            "post.liked",
            {"post_id": data["post_id"], "count": data["new_count"]},
        )

    def _on_comment(self, data: dict) -> None:
        self._send(
            post_group(data["post_id"]),
            "post.commented",
            {"post_id": data["post_id"], "comment_id": data.get("comment_id")},
        )
        owner = data.get("post_author_id")
        if owner and owner != data.get("author_id"):
            self._notify(
                owner,
                Notification.Type.COMMENT,
                {
                    "post_id": data["post_id"],
                    "actor_id": data.get("author_id"),
                    "body": data.get("body", ""),
                },
            )

    def _on_follow(self, data: dict) -> None:
        self._notify(
            data["followee_id"],
            Notification.Type.FOLLOW,
            {"actor_id": data["follower_id"]},
        )

    def _on_story(self, data: dict) -> None:
        # Live push of a new story into connected followers' bars needs the
        # author's follower set, which realtime-svc doesn't project (stories-svc
        # owns the story graph). For now the bar refreshes on navigation; a live
        # "new story" nudge is deferred. Subscribed so the topic exists.
        pass
