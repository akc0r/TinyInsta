import logging
import re
import uuid
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from tinyinsta.events import types

from posts import outbox
from posts.mongo import posts_collection, reposts_collection, saves_collection

logger = logging.getLogger(__name__)

_HASHTAG_RE = re.compile(r"#(\w+)")
_MENTION_RE = re.compile(r"@(\w+)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_hashtags(text: str) -> list[str]:
    return sorted({tag.lower() for tag in _HASHTAG_RE.findall(text or "")})


def _extract_mentions(text: str) -> list[str]:
    return sorted({name.lower() for name in _MENTION_RE.findall(text or "")})


def _mention_events(
    text: str, *, actor_id: str, source_type: str, source_id: str, post_id: str
) -> list[tuple[str, dict, str | None]]:
    return [
        (
            types.USER_MENTIONED,
            {
                "username": username,
                "actor_id": actor_id,
                "source_type": source_type,
                "source_id": source_id,
                "post_id": post_id,
            },
            None,
        )
        for username in _extract_mentions(text)
    ]


def _serialize(doc: dict) -> dict:
    return {
        "post_id": doc["_id"],
        "author_id": doc["author_id"],
        "caption": doc.get("caption", ""),
        "hashtags": doc.get("hashtags", []),
        "mentions": doc.get("mentions", []),
        "media_ids": doc.get("media_ids", []),
        "media_variants": doc.get("media_variants", {}),
        "kind": doc.get("kind", "post"),
        "comment_count": len(doc.get("comments", [])),
        "repost_count": doc.get("repost_count", 0),
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
        kind = "reel" if request.data.get("kind") == "reel" else "post"
        post_id = str(uuid.uuid4())
        author_id = str(request.user.user_id)
        created_at = _now()
        doc = {
            "_id": post_id,
            "author_id": author_id,
            "caption": caption,
            "hashtags": _extract_hashtags(caption),
            "mentions": _extract_mentions(caption),
            "media_ids": media_ids,
            "kind": kind,
            "comments": [],
            "repost_count": 0,
            "created_at": created_at,
        }

        events: list[tuple[str, dict, str | None]] = [
            (
                types.POST_CREATED,
                {
                    "post_id": post_id,
                    "author_id": author_id,
                    "caption": caption,
                    "hashtags": doc["hashtags"],
                    "kind": kind,
                    "created_at": created_at,
                },
                author_id,
            )
        ]
        events += _mention_events(
            caption, actor_id=author_id, source_type="post", source_id=post_id, post_id=post_id
        )

        outbox.write_atomically(
            lambda session: posts_collection().insert_one(doc, session=session), events
        )
        return Response(_serialize(doc), status=status.HTTP_201_CREATED)


class ReelsFeed(APIView):
    """Recent reels, newest first, keyset-paginated by created_at.

    `cursor` is the created_at of the last item from the prior page.
    """

    def get(self, request):
        cursor = request.query_params.get("cursor")
        try:
            limit = min(int(request.query_params.get("limit", 20)), 50)
        except ValueError:
            limit = 20
        query: dict = {"kind": "reel"}
        if cursor:
            query["created_at"] = {"$lt": cursor}
        docs = list(
            posts_collection().find(query).sort("created_at", -1).limit(limit)
        )
        items = [_serialize(d) for d in docs]
        next_cursor = docs[-1]["created_at"] if len(docs) == limit else None
        return Response({"items": items, "next_cursor": next_cursor})


class Tagged(APIView):
    """Posts that tag (mention) a username, newest first, keyset-paginated.

    `cursor` is the created_at of the last item from the prior page.
    """

    def get(self, request):
        username = (request.query_params.get("username") or "").lower()
        if not username:
            return Response(
                {"detail": "username query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cursor = request.query_params.get("cursor")
        try:
            limit = min(int(request.query_params.get("limit", 20)), 50)
        except ValueError:
            limit = 20
        query: dict = {"mentions": username}
        if cursor:
            query["created_at"] = {"$lt": cursor}
        docs = list(
            posts_collection().find(query).sort("created_at", -1).limit(limit)
        )
        items = [_serialize(d) for d in docs]
        next_cursor = docs[-1]["created_at"] if len(docs) == limit else None
        return Response({"items": items, "next_cursor": next_cursor})


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

        outbox.write_atomically(
            lambda session: posts_collection().delete_one({"_id": post_id}, session=session),
            [(types.POST_DELETED, {"post_id": post_id, "author_id": doc["author_id"]}, doc["author_id"])],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _serialize_comment(c: dict) -> dict:
    return {
        "comment_id": c["comment_id"],
        "author_id": c["author_id"],
        "body": c["body"],
        "parent_id": c.get("parent_id"),
        "edited": c.get("edited", False),
        "created_at": c["created_at"],
    }


class Comments(APIView):
    def get(self, request, post_id):
        doc = posts_collection().find_one({"_id": post_id}, {"comments": 1})
        if doc is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        comments = [
            _serialize_comment(c) for c in doc.get("comments", []) if not c.get("deleted")
        ]
        return Response({"items": comments})

    def post(self, request, post_id):
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body is required."}, status=status.HTTP_400_BAD_REQUEST)
        parent_id = request.data.get("parent_id")

        author_id = str(request.user.user_id)
        comment = {
            "comment_id": str(uuid.uuid4()),
            "author_id": author_id,
            "body": body,
            "parent_id": parent_id,
            "edited": False,
            "created_at": _now(),
        }
        doc = posts_collection().find_one({"_id": post_id}, {"author_id": 1, "comments": 1})
        if doc is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if parent_id and not any(
            c["comment_id"] == parent_id for c in doc.get("comments", [])
        ):
            return Response(
                {"detail": "parent comment not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        events: list[tuple[str, dict, str | None]] = [
            (
                types.POST_COMMENTED,
                {
                    "post_id": post_id,
                    "comment_id": comment["comment_id"],
                    "author_id": author_id,
                    "post_author_id": doc["author_id"],
                    "body": body,
                    "created_at": comment["created_at"],
                },
                post_id,
            )
        ]
        events += _mention_events(
            body,
            actor_id=author_id,
            source_type="comment",
            source_id=comment["comment_id"],
            post_id=post_id,
        )

        outbox.write_atomically(
            lambda session: posts_collection().update_one(
                {"_id": post_id}, {"$push": {"comments": comment}}, session=session
            ),
            events,
        )
        return Response(_serialize_comment(comment), status=status.HTTP_201_CREATED)


class CommentDetail(APIView):
    """Edit or delete a single comment (author of the comment, or post owner for delete)."""

    def patch(self, request, post_id, comment_id):
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body is required."}, status=status.HTTP_400_BAD_REQUEST)
        doc = posts_collection().find_one({"_id": post_id}, {"comments": 1})
        comment = _find_comment(doc, comment_id)
        if comment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if comment["author_id"] != str(request.user.user_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        edited_at = _now()
        outbox.write_atomically(
            lambda session: posts_collection().update_one(
                {"_id": post_id, "comments.comment_id": comment_id},
                {"$set": {"comments.$.body": body, "comments.$.edited": True}},
                session=session,
            ),
            [
                (
                    types.POST_COMMENT_EDITED,
                    {
                        "post_id": post_id,
                        "comment_id": comment_id,
                        "author_id": comment["author_id"],
                        "body": body,
                        "edited_at": edited_at,
                    },
                    post_id,
                )
            ],
        )
        return Response({"comment_id": comment_id, "body": body, "edited": True})

    def delete(self, request, post_id, comment_id):
        doc = posts_collection().find_one({"_id": post_id}, {"comments": 1, "author_id": 1})
        comment = _find_comment(doc, comment_id)
        if comment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        uid = str(request.user.user_id)
        # The comment author may delete their comment; the post owner may moderate.
        if comment["author_id"] != uid and doc["author_id"] != uid:
            return Response(status=status.HTTP_403_FORBIDDEN)

        outbox.write_atomically(
            lambda session: posts_collection().update_one(
                {"_id": post_id, "comments.comment_id": comment_id},
                {"$set": {"comments.$.deleted": True, "comments.$.body": ""}},
                session=session,
            ),
            [
                (
                    types.POST_COMMENT_DELETED,
                    {"post_id": post_id, "comment_id": comment_id, "author_id": uid},
                    post_id,
                )
            ],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _find_comment(doc: dict | None, comment_id: str) -> dict | None:
    if doc is None:
        return None
    for c in doc.get("comments", []):
        if c["comment_id"] == comment_id and not c.get("deleted"):
            return c
    return None


class Saves(APIView):
    """Save / unsave a post into a personal collection (bookmarks)."""

    def get(self, request):
        user_id = str(request.user.user_id)
        coll = request.query_params.get("collection")
        query = {"user_id": user_id}
        if coll:
            query["collection"] = coll
        items = [
            {"post_id": s["post_id"], "collection": s["collection"], "created_at": s["created_at"]}
            for s in saves_collection().find(query).sort("created_at", -1)
        ]
        return Response({"items": items})

    def post(self, request):
        post_id = request.data.get("post_id")
        if not post_id:
            return Response({"detail": "post_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        collection = request.data.get("collection") or "default"
        user_id = str(request.user.user_id)
        save = {
            "_id": f"{user_id}:{post_id}",  # one save per (user, post): no double-save
            "user_id": user_id,
            "post_id": post_id,
            "collection": collection,
            "created_at": _now(),
        }
        outbox.write_atomically(
            lambda session: saves_collection().update_one(
                {"_id": save["_id"]}, {"$set": save}, upsert=True, session=session
            ),
            [(types.POST_SAVED, {"post_id": post_id, "user_id": user_id, "collection": collection}, user_id)],
        )
        return Response({"post_id": post_id, "collection": collection}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        post_id = request.data.get("post_id") or request.query_params.get("post_id")
        if not post_id:
            return Response({"detail": "post_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        user_id = str(request.user.user_id)
        collection = request.data.get("collection") or "default"
        outbox.write_atomically(
            lambda session: saves_collection().delete_one(
                {"_id": f"{user_id}:{post_id}"}, session=session
            ),
            [(types.POST_UNSAVED, {"post_id": post_id, "user_id": user_id, "collection": collection}, user_id)],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class Reposts(APIView):
    """Repost a post onto the user's own timeline (and their followers')."""

    def post(self, request):
        post_id = request.data.get("post_id")
        if not post_id:
            return Response({"detail": "post_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        original = posts_collection().find_one({"_id": post_id}, {"author_id": 1})
        if original is None:
            return Response({"detail": "post not found."}, status=status.HTTP_404_NOT_FOUND)

        user_id = str(request.user.user_id)
        repost_id = str(uuid.uuid4())
        created_at = _now()
        repost = {
            "_id": repost_id,
            "user_id": user_id,
            "post_id": post_id,
            "author_id": original["author_id"],
            "created_at": created_at,
        }

        def _write(session):
            reposts_collection().insert_one(repost, session=session)
            posts_collection().update_one(
                {"_id": post_id}, {"$inc": {"repost_count": 1}}, session=session
            )

        outbox.write_atomically(
            _write,
            [
                (
                    types.POST_REPOSTED,
                    {
                        "repost_id": repost_id,
                        "post_id": post_id,
                        "user_id": user_id,
                        "author_id": original["author_id"],
                        "created_at": created_at,
                    },
                    user_id,
                )
            ],
        )
        return Response({"repost_id": repost_id, "post_id": post_id}, status=status.HTTP_201_CREATED)

    def delete(self, request, repost_id):
        repost = reposts_collection().find_one({"_id": repost_id})
        if repost is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if repost["user_id"] != str(request.user.user_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        def _write(session):
            reposts_collection().delete_one({"_id": repost_id}, session=session)
            posts_collection().update_one(
                {"_id": repost["post_id"]}, {"$inc": {"repost_count": -1}}, session=session
            )

        outbox.write_atomically(
            _write,
            [
                (
                    types.POST_UNREPOSTED,
                    {"repost_id": repost_id, "post_id": repost["post_id"], "user_id": repost["user_id"]},
                    repost["user_id"],
                )
            ],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
