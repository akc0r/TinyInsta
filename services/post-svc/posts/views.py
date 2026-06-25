import logging
import re
import uuid
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tinyinsta.bus import Producer
from tinyinsta.events import types

from posts.mongo import posts_collection

logger = logging.getLogger(__name__)

_producer = Producer()
_HASHTAG_RE = re.compile(r"#(\w+)")


def _extract_hashtags(caption: str) -> list[str]:
    return [tag.lower() for tag in _HASHTAG_RE.findall(caption or "")]


def _serialize(doc: dict) -> dict:
    return {
        "post_id": doc["_id"],
        "author_id": doc["author_id"],
        "caption": doc.get("caption", ""),
        "hashtags": doc.get("hashtags", []),
        "media_ids": doc.get("media_ids", []),
        "created_at": doc["created_at"],
    }


class PostList(APIView):
    def get(self, request):
        ids = request.query_params.get("ids")
        if not ids:
            return Response(
                {"detail": "ids query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        wanted = [i for i in ids.split(",") if i]
        docs = {d["_id"]: d for d in posts_collection().find({"_id": {"$in": wanted}})}
        items = [_serialize(docs[i]) for i in wanted if i in docs]
        return Response({"items": items})

    def post(self, request):
        caption = request.data.get("caption", "")
        media_ids = request.data.get("media_ids", [])
        post_id = str(uuid.uuid4())
        author_id = str(request.user.user_id)
        created_at = datetime.now(timezone.utc).isoformat()
        doc = {
            "_id": post_id,
            "author_id": author_id,
            "caption": caption,
            "hashtags": _extract_hashtags(caption),
            "media_ids": media_ids,
            "comments": [],
            "created_at": created_at,
        }
        posts_collection().insert_one(doc)

        try:
            _producer.publish(
                types.POST_CREATED,
                {
                    "post_id": post_id,
                    "author_id": author_id,
                    "caption": caption,
                    "hashtags": doc["hashtags"],
                    "created_at": created_at,
                },
                key=author_id,
            )
            _producer.flush()
        except Exception:  # noqa: BLE001 — a bus outage must not fail the write
            logger.warning("failed to publish post.created", exc_info=True)

        return Response(_serialize(doc), status=status.HTTP_201_CREATED)


class PostDetail(APIView):
    def get(self, request, post_id):
        doc = posts_collection().find_one({"_id": post_id})
        if doc is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize(doc))

    def delete(self, request, post_id):
        doc = posts_collection().find_one({"_id": post_id})
        if doc is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if doc["author_id"] != str(request.user.user_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        posts_collection().delete_one({"_id": post_id})

        try:
            _producer.publish(
                types.POST_DELETED,
                {"post_id": post_id, "author_id": doc["author_id"]},
                key=doc["author_id"],
            )
            _producer.flush()
        except Exception:  # noqa: BLE001
            logger.warning("failed to publish post.deleted", exc_info=True)

        return Response(status=status.HTTP_204_NO_CONTENT)


class Comments(APIView):
    def get(self, request, post_id):
        raise NotImplementedError

    def post(self, request, post_id):
        raise NotImplementedError
