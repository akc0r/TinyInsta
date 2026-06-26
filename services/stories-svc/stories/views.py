import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from tinyinsta.bus import Producer
from tinyinsta.events import types

from stories import store
from stories.models import Story
from stories.models import StoryView as StoryViewModel

logger = logging.getLogger(__name__)

_producer = Producer()


def _emit(event_type: str, data: dict, key: str) -> None:
    # A bus outage must never fail the write: the story is already durable in
    # Postgres + Redis. realtime-svc consumes story.created to light up the bar
    # of connected followers, but that is best-effort.
    try:
        _producer.publish(event_type, data, key=key)
        _producer.flush()
    except Exception:  # noqa: BLE001
        logger.warning("failed to publish %s", event_type, exc_info=True)


def _serialize(story: Story, viewed: bool = False) -> dict:
    return {
        "story_id": str(story.id),
        "author_id": str(story.author_id),
        "media_id": str(story.media_id),
        "audience": story.audience,
        "created_at": story.created_at.isoformat(),
        "expires_at": story.expires_at.isoformat(),
        "viewed": viewed,
    }


class StoryList(APIView):
    def post(self, request):
        media_id = request.data.get("media_id")
        if not media_id:
            return Response(
                {"detail": "media_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audience = request.data.get("audience", Story.Audience.PUBLIC)
        if audience not in Story.Audience.values:
            return Response(
                {"detail": f"audience must be one of {Story.Audience.values}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        author_id = str(request.user.user_id)
        ttl = settings.STORY_TTL_SECONDS
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        story = Story.objects.create(
            author_id=author_id,
            media_id=media_id,
            audience=audience,
            expires_at=expires_at,
        )
        # Refresh the live-bar marker to cover this newest story's lifetime.
        store.mark_active(author_id, ttl)
        _emit(
            types.STORY_CREATED,
            {"story_id": str(story.id), "author_id": author_id},
            key=author_id,
        )
        return Response(_serialize(story), status=status.HTTP_201_CREATED)


class StoryFeed(APIView):
    def get(self, request):
        viewer_id = str(request.user.user_id)
        # Candidates: accounts the viewer follows + themselves (own story first).
        candidates = store.following_of(viewer_id)
        candidates.append(viewer_id)
        live = store.active_authors(candidates)
        if not live:
            return Response({"items": []})

        now = datetime.now(timezone.utc)
        stories = list(
            Story.objects.filter(author_id__in=live, expires_at__gt=now).order_by(
                "created_at"
            )
        )
        seen = set(
            StoryViewModel.objects.filter(
                story__in=stories, viewer_id=viewer_id
            ).values_list("story_id", flat=True)
        )

        # A close-friends story is visible only to the author themselves and to
        # viewers in that author's close-friends set (a local Redis projection).
        by_author: dict[str, list[dict]] = defaultdict(list)
        for story in stories:
            author_id = str(story.author_id)
            if (
                story.audience == Story.Audience.CLOSE_FRIENDS
                and author_id != viewer_id
                and not store.is_close_friend(author_id, viewer_id)
            ):
                continue
            by_author[author_id].append(_serialize(story, viewed=story.id in seen))

        items = [
            {
                "author_id": author_id,
                "stories": items,
                "has_unseen": any(not s["viewed"] for s in items),
            }
            for author_id, items in by_author.items()
        ]
        # Your own story first, then accounts with unseen content, each by the
        # recency of their latest story.
        items.sort(
            key=lambda a: (
                a["author_id"] != viewer_id,
                not a["has_unseen"],
                -datetime.fromisoformat(a["stories"][-1]["created_at"]).timestamp(),
            )
        )
        return Response({"items": items})


class StoryView(APIView):
    def post(self, request, story_id):
        viewer_id = str(request.user.user_id)
        story = Story.objects.filter(id=story_id).first()
        if story is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            StoryViewModel.objects.create(story=story, viewer_id=viewer_id)
        except IntegrityError:
            pass  # already viewed — idempotent (composite uniqueness guard)
        else:
            # Only emit on the first view to keep the event meaningful.
            _emit(
                types.STORY_VIEWED,
                {"story_id": str(story.id), "viewer_id": viewer_id},
                key=str(story.id),
            )
        return Response({"story_id": str(story.id), "viewed": True})


class StoryViews(APIView):
    def get(self, request, story_id):
        story = Story.objects.filter(id=story_id).first()
        if story is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if str(story.author_id) != str(request.user.user_id):
            return Response(status=status.HTTP_403_FORBIDDEN)  # only the author
        views = story.views.order_by("-viewed_at")
        items = [
            {"viewer_id": str(v.viewer_id), "viewed_at": v.viewed_at.isoformat()}
            for v in views
        ]
        return Response({"items": items, "count": len(items)})
