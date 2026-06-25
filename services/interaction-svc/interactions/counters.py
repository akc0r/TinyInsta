from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def key(post_id: str) -> str:
    return f"likes:{post_id}"


# The like counter is a fast read model in Redis, derived from the Postgres
# `likes` relation (the system of record for *who* liked). It is rebuildable:
# if Redis is wiped, the next read/write re-projects it from Postgres. We
# write-through the authoritative Postgres count after each mutation rather than
# blind INCR/DECR, so the counter can never drift on retries/double-clicks
# (the (post_id, user_id) PK already makes the like itself idempotent).
def set_count(post_id: str, count: int) -> int:
    get_redis().set(key(post_id), count)
    return count


def get_count(post_id: str) -> int | None:
    value = get_redis().get(key(post_id))
    return int(value) if value is not None else None
