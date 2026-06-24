from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def key(author_id: str) -> str:
    return f"usertimeline:{author_id}"


def add_post(author_id: str, post_id: str, ts: float) -> None:
    raise NotImplementedError


def remove_post(author_id: str, post_id: str) -> None:
    raise NotImplementedError


def page(author_id: str, cursor: str | None, limit: int = 20) -> dict:
    raise NotImplementedError
