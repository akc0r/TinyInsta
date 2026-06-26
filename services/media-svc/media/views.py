import logging
import uuid
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tinyinsta.bus import Producer
from tinyinsta.events import types

from media import storage
from media.mongo import media_collection

logger = logging.getLogger(__name__)

_producer = Producer()


def _serialize(doc: dict) -> dict:
    return {
        "media_id": doc["_id"],
        "owner_id": doc["owner_id"],
        "kind": doc["kind"],
        "status": doc["status"],
        "original_url": doc["original_url"],
        "variants": doc.get("variants", {}),
        "created_at": doc["created_at"],
    }


class UploadUrl(APIView):
    def post(self, request):
        media_id = str(uuid.uuid4())
        object_key = f"{request.user.user_id}/{media_id}"
        return Response(
            {
                "media_id": media_id,
                "upload_url": storage.presigned_put_url(object_key),
                "object_url": storage.object_url(object_key),
            }
        )


class MediaList(APIView):
    def post(self, request):
        media_id = request.data.get("media_id")
        if not media_id:
            return Response(
                {"detail": "media_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        owner_id = str(request.user.user_id)
        object_key = f"{owner_id}/{media_id}"
        doc = {
            "_id": media_id,
            "owner_id": owner_id,
            "kind": request.data.get("kind", "image"),
            # Variants arrive asynchronously from media-worker (media.processed);
            # the original is already usable, so the post need not wait.
            "status": "pending",
            "original_url": storage.object_url(object_key),
            "variants": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        media_collection().replace_one({"_id": media_id}, doc, upsert=True)

        try:
            _producer.publish(
                types.MEDIA_UPLOADED,
                {
                    "media_id": media_id,
                    "kind": doc["kind"],
                    "original_url": doc["original_url"],
                },
                key=media_id,
            )
            _producer.flush()
        except Exception:  # noqa: BLE001 — a bus outage must not fail the upload
            logger.warning("failed to publish media.uploaded", exc_info=True)

        return Response(_serialize(doc), status=status.HTTP_201_CREATED)


class MediaDetail(APIView):
    def get(self, request, media_id):
        doc = media_collection().find_one({"_id": str(media_id)})
        if doc is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize(doc))
