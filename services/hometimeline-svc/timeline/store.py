from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def key(user_id: str) -> str:
    return f"home:{user_id}"


def fan_out(follower_ids: list[str], post_id: str, ts: float) -> None:
    raise NotImplementedError


def back_fill(follower_id: str, author_id: str) -> None:
    raise NotImplementedError


def remove_post(follower_ids: list[str], post_id: str) -> None:
    raise NotImplementedError


def page(user_id: str, cursor: str | None, limit: int = 20) -> dict:
    raise NotImplementedError
