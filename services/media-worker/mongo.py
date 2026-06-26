"""Media metadata access for the worker.

The worker is part of the **media bounded context** (media-svc + media-worker),
so it legitimately shares the `media` MongoDB collection — this is not a service
reaching into another service's database.
"""

from __future__ import annotations

import os
from functools import lru_cache

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.environ.get("MONGO_DB", "media_svc")


@lru_cache(maxsize=1)
def _media_collection():
    from pymongo import MongoClient

    return MongoClient(MONGO_URI)[MONGO_DB]["media"]


def mark_ready(media_id: str, variants: dict[str, str]) -> None:
    """Flip the media to `ready` and record the produced variants."""
    _media_collection().update_one(
        {"_id": media_id},
        {"$set": {"status": "ready", "variants": variants}},
    )
