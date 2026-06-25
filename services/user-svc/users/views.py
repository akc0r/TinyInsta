import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tinyinsta.bus import Producer
from tinyinsta.events import types

from users import graph
from users.models import Profile
from users.provisioning import get_or_create_profile
from users.serializers import ProfileSerializer

logger = logging.getLogger(__name__)

_producer = Producer()


def _profile_payload(profile: Profile, viewer_id: str | None = None) -> dict:
    """Serialize a profile and enrich it with graph-derived fields.

    `followers` / `following` counts come from Neo4j; `is_following` reflects
    whether `viewer_id` follows this profile (omitted when looking at oneself).
    """
    data = ProfileSerializer(profile).data
    target_id = str(profile.user_id)
    data.update(graph.counts(target_id))
    if viewer_id is not None and viewer_id != target_id:
        data["is_following"] = graph.is_following(viewer_id, target_id)
    return data


def _hydrate(user_ids: list[str]) -> list[dict]:
    """Look up profiles for the given ids, preserving the input order."""
    by_id = {
        str(p.user_id): ProfileSerializer(p).data
        for p in Profile.objects.filter(user_id__in=user_ids)
    }
    return [by_id[uid] for uid in user_ids if uid in by_id]


class Me(APIView):
    def get(self, request):
        profile, _ = get_or_create_profile(request.user)
        return Response(_profile_payload(profile))

    def patch(self, request):
        profile, _ = get_or_create_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(_profile_payload(profile))


class ProfileDetail(APIView):
    def get(self, request, user_id):
        try:
            profile = Profile.objects.get(user_id=user_id)
        except Profile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_profile_payload(profile, str(request.user.user_id)))


# --- Social graph (Phase 3) -------------------------------------------------
class Follow(APIView):
    def post(self, request, user_id):
        follower_id = str(request.user.user_id)
        followee_id = str(user_id)
        if follower_id == followee_id:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Profile.objects.filter(user_id=user_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        graph.follow(follower_id, followee_id)
        self._publish(types.USER_FOLLOWED, follower_id, followee_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, user_id):
        follower_id = str(request.user.user_id)
        followee_id = str(user_id)
        graph.unfollow(follower_id, followee_id)
        self._publish(types.USER_UNFOLLOWED, follower_id, followee_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _publish(event_type: str, follower_id: str, followee_id: str) -> None:
        try:
            _producer.publish(
                event_type,
                {"follower_id": follower_id, "followee_id": followee_id},
                key=follower_id,
            )
            _producer.flush()
        except Exception:  # noqa: BLE001 — a bus outage must not fail the write
            logger.warning("failed to publish %s", event_type, exc_info=True)


class Followers(APIView):
    def get(self, request, user_id):
        return Response({"items": _hydrate(graph.follower_ids(str(user_id)))})


class Following(APIView):
    def get(self, request, user_id):
        return Response({"items": _hydrate(graph.following_ids(str(user_id)))})


class Suggestions(APIView):
    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 10)), 50)
        except ValueError:
            limit = 10
        ranked = graph.suggestions(str(request.user.user_id), limit)
        profiles = {p["user_id"]: p for p in _hydrate([r["user_id"] for r in ranked])}
        items = [
            {**profiles[r["user_id"]], "mutual": r["mutual"]}
            for r in ranked
            if r["user_id"] in profiles
        ]
        return Response({"items": items})
