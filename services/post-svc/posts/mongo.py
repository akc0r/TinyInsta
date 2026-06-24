from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_db():
    from pymongo import MongoClient

    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB]


def posts_collection():
    return get_db()["posts"]
