from __future__ import annotations

import logging

import mongo
from processors import images, videos
from tinyinsta.bus import Consumer, Producer, redis_dedupe_store
from tinyinsta.events import Envelope, types

logging.basicConfig(level="INFO")
logger = logging.getLogger("media-worker")

GROUP_ID = "media-worker"

_producer = Producer()


def handle(envelope: Envelope) -> None:
    if envelope.type != types.MEDIA_UPLOADED:
        return
    data = envelope.data
    media_id, kind = data["media_id"], data["kind"]

    if kind == "image":
        variants = images.process(data["original_url"])
    elif kind == "video":
        variants = videos.process(data["original_url"])
    else:
        logger.warning("media-worker.unknown_kind", extra={"kind": kind})
        return

    # Flip the media doc to `ready` before announcing it, so consumers that come
    # back to GET /media/{id} always find the variants the event advertises.
    mongo.mark_ready(media_id, variants)

    _producer.publish(
        types.MEDIA_PROCESSED,
        {"media_id": media_id, "variants": variants},
        key=media_id,
    )
    _producer.flush()
    logger.info(
        "media-worker.processed",
        extra={"media_id": media_id, "variants": list(variants)},
    )


def main() -> None:
    consumer = Consumer(
        topics=[types.MEDIA_UPLOADED],
        group_id=GROUP_ID,
        dedupe=redis_dedupe_store(GROUP_ID),
    )
    consumer.run(handle)


if __name__ == "__main__":
    main()
