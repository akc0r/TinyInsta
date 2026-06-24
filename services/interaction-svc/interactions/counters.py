from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def key(post_id: str) -> str:
    return f"likes:{post_id}"


def incr(post_id: str) -> int:
    raise NotImplementedError


def decr(post_id: str) -> int:
    raise NotImplementedError
