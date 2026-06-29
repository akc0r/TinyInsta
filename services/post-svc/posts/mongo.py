from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_db():
    from pymongo import MongoClient

    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB]


def posts_collection():
    return get_db()["posts"]


def saves_collection():
    # _id = "{user_id}:{post_id}" enforces one save per (user, post).
    return get_db()["saves"]


def reposts_collection():
    return get_db()["reposts"]
