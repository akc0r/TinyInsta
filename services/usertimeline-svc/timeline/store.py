from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def key(author_id: str) -> str:
    return f"usertimeline:{author_id}"


def add_post(author_id: str, post_id: str, ts: float) -> None:
    get_redis().zadd(key(author_id), {post_id: ts})


def remove_post(author_id: str, post_id: str) -> None:
    get_redis().zrem(key(author_id), post_id)


def page(author_id: str, cursor: str | None, limit: int = 20) -> dict:
    """Keyset pagination over the sorted set, newest first.

    `cursor` is the score of the last item from the previous page; it is
    excluded so pages never overlap. Returns the post ids plus the score to
    pass as the next cursor (None when the last page has been reached).
    """
    max_score = f"({cursor}" if cursor else "+inf"
    rows = get_redis().zrevrangebyscore(
        key(author_id),
        max_score,
        "-inf",
        start=0,
        num=limit,
        withscores=True,
    )
    items = [post_id for post_id, _ in rows]
    next_cursor = rows[-1][1] if len(rows) == limit else None
    return {"items": items, "next_cursor": next_cursor}
