from functools import lru_cache

from django.conf import settings

from timeline import clients

# A home timeline is capped to its most recent entries: a feed nobody scrolls to
# the bottom of doesn't need unbounded history, and the cap bounds Redis memory.
MAX_HOME = 1000


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def home_key(user_id: str) -> str:
    return f"home:{user_id}"


def followers_key(author_id: str) -> str:
    return f"followers:{author_id}"


# --- Follower graph cache ---------------------------------------------------
# A local projection of the social graph, built from user.followed /
# user.unfollowed events, so fan-out on post.created never has to call user-svc
# on the hot path. Rebuildable by replaying the user.* topics.
def add_follower(author_id: str, follower_id: str) -> None:
    get_redis().sadd(followers_key(author_id), follower_id)


def remove_follower(author_id: str, follower_id: str) -> None:
    get_redis().srem(followers_key(author_id), follower_id)


def followers_of(author_id: str) -> list[str]:
    return list(get_redis().smembers(followers_key(author_id)))


def _trim(pipe, key: str) -> None:
    """Drop everything past the newest MAX_HOME entries (lowest scores first)."""
    pipe.zremrangebyrank(key, 0, -(MAX_HOME + 1))


# --- Fan-out on write -------------------------------------------------------
def fan_out(target_ids: list[str], post_id: str, ts: float) -> None:
    """Push a post into each target's home timeline (followers + the author)."""
    if not target_ids:
        return
    pipe = get_redis().pipeline()
    for user_id in target_ids:
        key = home_key(user_id)
        pipe.zadd(key, {post_id: ts})
        _trim(pipe, key)
    pipe.execute()


def remove_post(target_ids: list[str], post_id: str) -> None:
    """Remove a deleted post from every home timeline it was pushed to."""
    if not target_ids:
        return
    pipe = get_redis().pipeline()
    for user_id in target_ids:
        pipe.zrem(home_key(user_id), post_id)
    pipe.execute()


# --- Back-fill / purge on follow changes ------------------------------------
def back_fill(follower_id: str, author_id: str) -> None:
    """Inject the followee's recent posts into a new follower's home timeline.

    Posts are read from usertimeline-svc with their original scores so they
    land in chronological position rather than all bunched at "now".
    """
    posts = clients.recent_posts(author_id)
    if not posts:
        return
    key = home_key(follower_id)
    pipe = get_redis().pipeline()
    pipe.zadd(key, {post_id: score for post_id, score in posts})
    _trim(pipe, key)
    pipe.execute()


def purge(follower_id: str, author_id: str) -> None:
    """Remove the (now unfollowed) author's posts from the follower's timeline.

    Best-effort: only the posts still in the author's recent window are pulled;
    older ones have already aged out of the capped home timeline anyway.
    """
    post_ids = [post_id for post_id, _ in clients.recent_posts(author_id)]
    if post_ids:
        get_redis().zrem(home_key(follower_id), *post_ids)


# --- Read -------------------------------------------------------------------
def page(user_id: str, cursor: str | None, limit: int = 20) -> dict:
    """Keyset pagination over the home timeline, newest first.

    `cursor` is the score of the last item from the previous page; it is
    excluded so pages never overlap. `next_cursor` is None on the last page.
    """
    max_score = f"({cursor}" if cursor else "+inf"
    rows = get_redis().zrevrangebyscore(
        home_key(user_id),
        max_score,
        "-inf",
        start=0,
        num=limit,
        withscores=True,
    )
    items = [post_id for post_id, _ in rows]
    next_cursor = rows[-1][1] if len(rows) == limit else None
    return {"items": items, "next_cursor": next_cursor}
