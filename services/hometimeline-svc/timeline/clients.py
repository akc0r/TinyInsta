"""Synchronous reads of usertimeline-svc.

The per-author read model (usertimeline-svc) is the source hometimeline-svc
pulls from when a follow happens (back-fill) or breaks (purge). The same call
is the building block the hybrid/celebrity read path will reuse later.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


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
