import logging

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tinyinsta.bus import Producer
from tinyinsta.events import types

from interactions import counters
from interactions.models import Like as LikeModel

logger = logging.getLogger(__name__)

_producer = Producer()


def _emit(event_type: str, post_id: str, user_id: str, new_count: int) -> None:
    # A bus outage must never fail the like itself; realtime-svc consumes this to
    # push the live counter, but the write is already durable in Postgres/Redis.
    try:
        _producer.publish(
            event_type,
            {"post_id": post_id, "user_id": user_id, "new_count": new_count},
            key=post_id,
        )
        _producer.flush()
    except Exception:  # noqa: BLE001
        logger.warning("failed to publish %s", event_type, exc_info=True)


class Like(APIView):
    def post(self, request, post_id):
        pid, uid = str(post_id), str(request.user.user_id)
        try:
            LikeModel.objects.create(post_id=pid, user_id=uid)
        except IntegrityError:
            pass  # already liked — idempotent (composite PK guard)
        count = counters.set_count(pid, LikeModel.objects.filter(post_id=pid).count())
        _emit(types.POST_LIKED, pid, uid, count)
        return Response({"post_id": pid, "liked": True, "count": count})

    def delete(self, request, post_id):
        pid, uid = str(post_id), str(request.user.user_id)
        LikeModel.objects.filter(post_id=pid, user_id=uid).delete()
        count = counters.set_count(pid, LikeModel.objects.filter(post_id=pid).count())
        _emit(types.POST_UNLIKED, pid, uid, count)
        return Response({"post_id": pid, "liked": False, "count": count})


class LikeCount(APIView):
    def get(self, request, post_id):
        pid, uid = str(post_id), str(request.user.user_id)
        count = counters.get_count(pid)
        if count is None:  # cold Redis key → re-project from the Postgres truth
            count = counters.set_count(pid, LikeModel.objects.filter(post_id=pid).count())
        liked = LikeModel.objects.filter(post_id=pid, user_id=uid).exists()
        return Response({"post_id": pid, "count": count, "liked": liked})
