"""Synchronous reads of usertimeline-svc.

The per-author read model (usertimeline-svc) is the source hometimeline-svc
pulls from when a follow happens (back-fill) or breaks (purge). The same call
is the building block the hybrid/celebrity read path will reuse later.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def rank(viewer_id: str, post_ids: list[str]) -> list[str] | None:
    """Ask ranking-svc to order ``post_ids`` for ``viewer_id``.

    Returns the ranked id list, or ``None`` if ranking is disabled or unreachable.
    """
    if not getattr(settings, "RANKING_ENABLED", False) or not post_ids:
        return None
    try:
        resp = requests.post(
            f"{settings.RANKING_URL}/ranking/score",
            json={"viewer_id": viewer_id, "items": post_ids},
            timeout=2,
        )
        resp.raise_for_status()
        return resp.json().get("ranked")
    except (requests.RequestException, ValueError):
        logger.warning("ranking call failed; falling back to chronological", exc_info=True)
        return None


def recent_posts(author_id: str, limit: int = 30) -> list[tuple[str, float]]:
    """Return an author's recent posts as `(post_id, score)` pairs, newest first.

    Best-effort: a usertimeline-svc hiccup must not fail follow processing, so
    any error yields an empty list (the back-fill simply doesn't happen).
    """
    url = f"{settings.USERTIMELINE_URL}/usertimeline/{author_id}"
    try:
        resp = requests.get(
            url, params={"limit": limit, "withscores": 1}, timeout=3
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except (requests.RequestException, ValueError):
        logger.warning("usertimeline read failed for %s", author_id, exc_info=True)
        return []
    return [(post_id, float(score)) for post_id, score in items]
