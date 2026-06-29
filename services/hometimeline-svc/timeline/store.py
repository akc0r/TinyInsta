from functools import lru_cache

from django.conf import settings
from prometheus_client import Counter, Histogram

from timeline import clients

# A home timeline is capped to its most recent entries: a feed nobody scrolls to
# the bottom of doesn't need unbounded history, and the cap bounds Redis memory.
MAX_HOME = 1000

# --- Fan-out observability --------------------------------------------------
# Surfaced on /metrics → Grafana: how wide and how slow each write-time fan-out
# is (the cost the hybrid celebrity path exists to cap), plus how often the
# read-time celebrity pull fires.
FANOUT_TARGETS = Histogram(
    "hometimeline_fanout_targets",
    "Number of home timelines a single post was fanned out to",
    buckets=(1, 5, 10, 50, 100, 500, 1000, 5000),
)
FANOUT_SECONDS = Histogram(
    "hometimeline_fanout_seconds", "Wall-clock duration of a write-time fan-out"
)
CELEB_PULLS = Counter(
    "hometimeline_celebrity_pulls_total",
    "Read-time pulls of a celebrity's posts merged into a home page",
)
CELEB_PROMOTIONS = Counter(
    "hometimeline_celebrity_promotions_total", "Accounts promoted to celebrity"
)
CELEB_DEMOTIONS = Counter(
    "hometimeline_celebrity_demotions_total", "Accounts demoted from celebrity"
)


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def home_key(user_id: str) -> str:
    return f"home:{user_id}"


def followers_key(author_id: str) -> str:
    return f"followers:{author_id}"


def following_key(user_id: str) -> str:
    return f"following:{user_id}"


# Global set of accounts that have crossed the celebrity threshold. We pull their
# posts at read time instead of fanning out on write — see the hybrid path below.
CELEBRITIES_KEY = "celebrities"


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


def add_following(follower_id: str, author_id: str) -> None:
    get_redis().sadd(following_key(follower_id), author_id)


def remove_following(follower_id: str, author_id: str) -> None:
    get_redis().srem(following_key(follower_id), author_id)


# --- Celebrity (hybrid) bookkeeping ----------------------------------------
def is_celebrity(author_id: str) -> bool:
    """True once an author's follower count crosses the celebrity threshold.

    Evaluated against the local follower cache, so no cross-service call on the
    hot path. Above this line we stop fanning out the author's posts on write.
    """
    return get_redis().scard(followers_key(author_id)) >= settings.CELEBRITY_FOLLOWER_THRESHOLD


def mark_celebrity(author_id: str) -> None:
    # sadd returns 1 only on the first add → count a promotion once.
    if get_redis().sadd(CELEBRITIES_KEY, author_id):
        CELEB_PROMOTIONS.inc()


def demote_if_below(author_id: str) -> None:
    """Drop an account back to push fan-out once it falls under the threshold.

    Without this, a previously-celebrity account that loses followers would stay
    in the pull set forever (read-time cost it no longer warrants, and its new
    posts would never be pushed to its followers). Called on unfollow.
    """
    if get_redis().scard(followers_key(author_id)) < settings.CELEBRITY_FOLLOWER_THRESHOLD:
        if get_redis().srem(CELEBRITIES_KEY, author_id):
            CELEB_DEMOTIONS.inc()


def celebs_followed(follower_id: str) -> list[str]:
    """The celebrities a given user follows (intersection of two Redis sets)."""
    return list(get_redis().sinter(following_key(follower_id), CELEBRITIES_KEY))


def _trim(pipe, key: str) -> None:
    """Drop everything past the newest MAX_HOME entries (lowest scores first)."""
    pipe.zremrangebyrank(key, 0, -(MAX_HOME + 1))


# --- Fan-out on write -------------------------------------------------------
def fan_out(target_ids: list[str], post_id: str, ts: float) -> None:
    """Push a post into each target's home timeline (followers + the author)."""
    if not target_ids:
        return
    FANOUT_TARGETS.observe(len(target_ids))
    with FANOUT_SECONDS.time():
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


# --- Read (hybrid: push ⊕ celebrity pull) -----------------------------------
def page(user_id: str, cursor: str | None, limit: int = 20) -> dict:
    """Keyset pagination over the home timeline, newest first.

    Hybrid read: the push-based entries in ``home:{user}`` (posts fanned out by
    normal accounts) are merged at read time with the recent posts of every
    celebrity the user follows — pulled from usertimeline-svc rather than stored
    per-follower. `cursor` is the score (epoch seconds) of the last item from the
    previous page; it is excluded so pages never overlap.
    """
    max_cursor = float(cursor) if cursor else None
    candidates: dict[str, float] = {}

    # 1. Push entries: the `limit` highest-scoring posts below the cursor.
    max_score = f"({cursor}" if cursor else "+inf"
    for post_id, score in get_redis().zrevrangebyscore(
        home_key(user_id), max_score, "-inf", start=0, num=limit, withscores=True
    ):
        candidates[post_id] = score

    # 2. Pull entries: recent posts of each celebrity followed, merged in.
    #    (Deep pagination beyond a celebrity's recent window is best-effort.)
    for celeb_id in celebs_followed(user_id):
        CELEB_PULLS.inc()
        for post_id, score in clients.recent_posts(celeb_id):
            if max_cursor is None or score < max_cursor:
                candidates[post_id] = score

    # 3. Merge by score (timestamp) desc, take the page. The cursor stays
    #    chronological so keyset pagination remains stable across pages.
    merged = sorted(candidates.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    items = [post_id for post_id, _ in merged]
    next_cursor = merged[-1][1] if len(merged) == limit else None

    # 4. Optional algorithmic re-rank *within* the page: ranking-svc reorders the
    #    page's posts by recency⊕engagement⊕affinity. Pagination remains keyset by
    #    timestamp (next_cursor unchanged); only intra-page order is affected. If
    #    ranking is off/unreachable the chronological order stands.
    ranked = clients.rank(user_id, items)
    if ranked:
        in_page = set(items)
        items = [pid for pid in ranked if pid in in_page]

    return {"items": items, "next_cursor": next_cursor}
