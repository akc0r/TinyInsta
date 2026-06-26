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
        "media_variants": doc.get("media_variants", {}),
        "comment_count": len(doc.get("comments", [])),
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


def _serialize_comment(c: dict) -> dict:
    return {
        "comment_id": c["comment_id"],
        "author_id": c["author_id"],
        "body": c["body"],
        "created_at": c["created_at"],
    }


class Comments(APIView):
    def get(self, request, post_id):
        doc = posts_collection().find_one({"_id": post_id}, {"comments": 1})
        if doc is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        comments = [_serialize_comment(c) for c in doc.get("comments", [])]
        return Response({"items": comments})

    def post(self, request, post_id):
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response(
                {"detail": "body is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        comment = {
            "comment_id": str(uuid.uuid4()),
            "author_id": str(request.user.user_id),
            "body": body,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        # Comments stay embedded in the post document (reasonable volume).
        result = posts_collection().update_one(
            {"_id": post_id}, {"$push": {"comments": comment}}
        )
        if result.matched_count == 0:
            return Response(status=status.HTTP_404_NOT_FOUND)

        doc = posts_collection().find_one({"_id": post_id}, {"author_id": 1})
        try:
            _producer.publish(
                types.POST_COMMENTED,
                {
                    "post_id": post_id,
                    "comment_id": comment["comment_id"],
                    "author_id": comment["author_id"],
                    # The post owner travels with the event so realtime-svc can
                    # notify them without a sync call back here.
                    "post_author_id": doc["author_id"],
                    "body": body,
                    "created_at": comment["created_at"],
                },
                key=post_id,
            )
            _producer.flush()
        except Exception:  # noqa: BLE001
            logger.warning("failed to publish post.commented", exc_info=True)

        return Response(_serialize_comment(comment), status=status.HTTP_201_CREATED)
