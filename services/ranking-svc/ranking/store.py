"""Ranking signals + scoring, backed by Redis.

Per-post engagement + metadata and per-(viewer, author) affinity, built from the
post.* events. The score blends recency (exponential decay), log-damped
engagement and affinity, plus a small boost for reels. Weights are env-tunable.
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from functools import lru_cache

from django.conf import settings

# Signal TTL (30 days).
SIGNAL_TTL = 30 * 24 * 3600


@lru_cache(maxsize=1)
def get_redis():
    import redis

    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _meta_key(post_id: str) -> str:
    return f"rank:meta:{post_id}"


def _eng_key(post_id: str) -> str:
    return f"rank:eng:{post_id}"


def _affinity_key(viewer_id: str, author_id: str) -> str:
    return f"rank:aff:{viewer_id}:{author_id}"


# --- Signal ingestion (from the bus) ----------------------------------------
def record_post(post_id: str, author_id: str, created_at: str, kind: str = "post") -> None:
    r = get_redis()
    r.hset(_meta_key(post_id), mapping={"author_id": author_id, "created_at": created_at, "kind": kind})
    r.expire(_meta_key(post_id), SIGNAL_TTL)


def author_of(post_id: str) -> str | None:
    return get_redis().hget(_meta_key(post_id), "author_id")


def add_engagement(post_id: str, weight: float) -> None:
    r = get_redis()
    r.incrbyfloat(_eng_key(post_id), weight)
    r.expire(_eng_key(post_id), SIGNAL_TTL)


def bump_affinity(viewer_id: str, author_id: str, weight: float = 1.0) -> None:
    if not author_id or viewer_id == author_id:
        return
    r = get_redis()
    r.incrbyfloat(_affinity_key(viewer_id, author_id), weight)
    r.expire(_affinity_key(viewer_id, author_id), SIGNAL_TTL)


def remove_post(post_id: str) -> None:
    get_redis().delete(_meta_key(post_id), _eng_key(post_id))


# --- Scoring (read time) ----------------------------------------------------
def _recency(created_at: str, now: float) -> float:
    try:
        ts = datetime.fromisoformat(created_at).timestamp()
    except (ValueError, TypeError):
        return 0.0
    age_h = max(0.0, (now - ts) / 3600.0)
    return 0.5 ** (age_h / settings.RANK_RECENCY_HALF_LIFE_H)


def score_many(viewer_id: str, post_ids: list[str]) -> dict[str, float]:
    """Return a score per post id. Unknown posts (no metadata) score 0."""
    if not post_ids:
        return {}
    r = get_redis()
    now = time.time()

    pipe = r.pipeline()
    for pid in post_ids:
        pipe.hgetall(_meta_key(pid))
        pipe.get(_eng_key(pid))
    raw = pipe.execute()

    # Affinity for the distinct authors in this batch.
    metas = {pid: raw[2 * i] for i, pid in enumerate(post_ids)}
    engs = {pid: raw[2 * i + 1] for i, pid in enumerate(post_ids)}
    authors = {m.get("author_id") for m in metas.values() if m}
    authors.discard(None)
    aff_pipe = r.pipeline()
    author_list = list(authors)
    for author_id in author_list:
        aff_pipe.get(_affinity_key(viewer_id, author_id))
    aff_vals = aff_pipe.execute() if author_list else []
    affinity = {
        author_list[i]: float(aff_vals[i] or 0.0) for i in range(len(author_list))
    }

    scores: dict[str, float] = {}
    for pid in post_ids:
        meta = metas.get(pid) or {}
        if not meta:
            scores[pid] = 0.0
            continue
        recency = _recency(meta.get("created_at", ""), now)
        engagement = math.log1p(float(engs.get(pid) or 0.0))
        aff = math.log1p(affinity.get(meta.get("author_id"), 0.0))
        reel_boost = settings.RANK_W_REEL if meta.get("kind") == "reel" else 0.0
        scores[pid] = (
            settings.RANK_W_RECENCY * recency
            + settings.RANK_W_ENGAGEMENT * engagement
            + settings.RANK_W_AFFINITY * aff
            + reel_boost
        )
    return scores
