from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def following_key(viewer_id: str) -> str:
    return f"following:{viewer_id}"


def active_key(author_id: str) -> str:
    return f"story:active:{author_id}"


def close_friends_key(owner_id: str) -> str:
    return f"close_friends:{owner_id}"


# --- Following graph cache --------------------------------------------------
# A local projection of *who each viewer follows*, built from user.followed /
# user.unfollowed events. The story bar shows the active stories of followed
# accounts, so the feed query needs this set without calling user-svc on the
# read path. Rebuildable by replaying the user.* topics.
def add_following(follower_id: str, followee_id: str) -> None:
    get_redis().sadd(following_key(follower_id), followee_id)


def remove_following(follower_id: str, followee_id: str) -> None:
    get_redis().srem(following_key(follower_id), followee_id)


def following_of(viewer_id: str) -> list[str]:
    return list(get_redis().smembers(following_key(viewer_id)))


# --- Close-friends graph cache ----------------------------------------------
# A projection of each author's close-friends set, built from
# user.close_friend_added / removed. A close-friends story is shown only to
# viewers in the author's set. Rebuildable by replaying the user.* topics.
def add_close_friend(owner_id: str, friend_id: str) -> None:
    get_redis().sadd(close_friends_key(owner_id), friend_id)


def remove_close_friend(owner_id: str, friend_id: str) -> None:
    get_redis().srem(close_friends_key(owner_id), friend_id)


def is_close_friend(owner_id: str, viewer_id: str) -> bool:
    return bool(get_redis().sismember(close_friends_key(owner_id), viewer_id))


# --- "Live" story bar marker ------------------------------------------------
# story:active:{author_id} is a TTL key that simply records "this author has a
# story live right now". It expires on its own after the story's lifetime, so
# the bar self-clears with no computation (see docs/stories-svc.md). The key is
# (re)set to the longest remaining lifetime each time the author posts a story.
def mark_active(author_id: str, ttl_seconds: int) -> None:
    get_redis().set(active_key(author_id), "1", ex=ttl_seconds)


def active_authors(author_ids: list[str]) -> set[str]:
    """Return the subset of author_ids that currently have a live story."""
    if not author_ids:
        return set()
    pipe = get_redis().pipeline()
    for author_id in author_ids:
        pipe.exists(active_key(author_id))
    return {aid for aid, present in zip(author_ids, pipe.execute()) if present}
