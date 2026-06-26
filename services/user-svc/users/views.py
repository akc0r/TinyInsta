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


def _publish(event_type: str, data: dict, key: str) -> None:
    # A bus outage must never fail the write; the graph mutation is already
    # durable in Neo4j and the read models will converge once the bus recovers.
    try:
        _producer.publish(event_type, data, key=key)
        _producer.flush()
    except Exception:  # noqa: BLE001
        logger.warning("failed to publish %s", event_type, exc_info=True)


def _profile_payload(profile: Profile, viewer_id: str | None = None) -> dict:
    """Serialize a profile and enrich it with graph-derived fields.

    `followers` / `following` counts come from Neo4j; `is_following`,
    `is_blocking` and `is_close_friend` reflect the viewer's relationship to
    this profile (all omitted when looking at oneself).
    """
    data = ProfileSerializer(profile).data
    target_id = str(profile.user_id)
    data.update(graph.counts(target_id))
    if viewer_id is not None and viewer_id != target_id:
        data["is_following"] = graph.is_following(viewer_id, target_id)
        data["is_blocking"] = graph.is_blocking(viewer_id, target_id)
        data["is_close_friend"] = graph.is_close_friend(viewer_id, target_id)
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
        viewer_id = str(request.user.user_id)
        # A user who blocked you is invisible — same response as not existing.
        if graph.is_blocking(str(user_id), viewer_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_profile_payload(profile, viewer_id))


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
        if graph.blocks_either(follower_id, followee_id):
            return Response(
                {"detail": "Following is not possible between blocked users."},
                status=status.HTTP_403_FORBIDDEN,
            )

        graph.follow(follower_id, followee_id)
        _publish(
            types.USER_FOLLOWED,
            {"follower_id": follower_id, "followee_id": followee_id},
            key=follower_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, user_id):
        follower_id = str(request.user.user_id)
        followee_id = str(user_id)
        graph.unfollow(follower_id, followee_id)
        _publish(
            types.USER_UNFOLLOWED,
            {"follower_id": follower_id, "followee_id": followee_id},
            key=follower_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class Block(APIView):
    def post(self, request, user_id):
        blocker_id = str(request.user.user_id)
        blocked_id = str(user_id)
        if blocker_id == blocked_id:
            return Response(
                {"detail": "You cannot block yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Profile.objects.filter(user_id=user_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Blocking severs follows + close-friend edges both ways; emit the
        # matching events so home/story feeds purge the now-hidden content.
        removed = graph.block(blocker_id, blocked_id)
        _publish(
            types.USER_BLOCKED,
            {"blocker_id": blocker_id, "blocked_id": blocked_id},
            key=blocker_id,
        )
        if removed["a_followed_b"]:
            _publish(
                types.USER_UNFOLLOWED,
                {"follower_id": blocker_id, "followee_id": blocked_id},
                key=blocker_id,
            )
        if removed["b_followed_a"]:
            _publish(
                types.USER_UNFOLLOWED,
                {"follower_id": blocked_id, "followee_id": blocker_id},
                key=blocked_id,
            )
        if removed["a_close_b"]:
            _publish(
                types.USER_CLOSE_FRIEND_REMOVED,
                {"owner_id": blocker_id, "friend_id": blocked_id},
                key=blocker_id,
            )
        if removed["b_close_a"]:
            _publish(
                types.USER_CLOSE_FRIEND_REMOVED,
                {"owner_id": blocked_id, "friend_id": blocker_id},
                key=blocked_id,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, user_id):
        blocker_id = str(request.user.user_id)
        blocked_id = str(user_id)
        graph.unblock(blocker_id, blocked_id)
        _publish(
            types.USER_UNBLOCKED,
            {"blocker_id": blocker_id, "blocked_id": blocked_id},
            key=blocker_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CloseFriend(APIView):
    def post(self, request, user_id):
        owner_id = str(request.user.user_id)
        friend_id = str(user_id)
        if owner_id == friend_id:
            return Response(
                {"detail": "You cannot add yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not Profile.objects.filter(user_id=user_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        if graph.blocks_either(owner_id, friend_id):
            return Response(
                {"detail": "Cannot add a blocked user."},
                status=status.HTTP_403_FORBIDDEN,
            )

        graph.add_close_friend(owner_id, friend_id)
        _publish(
            types.USER_CLOSE_FRIEND_ADDED,
            {"owner_id": owner_id, "friend_id": friend_id},
            key=owner_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, user_id):
        owner_id = str(request.user.user_id)
        friend_id = str(user_id)
        graph.remove_close_friend(owner_id, friend_id)
        _publish(
            types.USER_CLOSE_FRIEND_REMOVED,
            {"owner_id": owner_id, "friend_id": friend_id},
            key=owner_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CloseFriends(APIView):
    def get(self, request):
        return Response(
            {"items": _hydrate(graph.close_friend_ids(str(request.user.user_id)))}
        )


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
