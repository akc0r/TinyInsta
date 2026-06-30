"""Per-user rate limiting, shared across services.

A Redis fixed-window counter keyed by the Keycloak user id. Fail-open: a request
is allowed if Redis is unreachable.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from rest_framework.throttling import BaseThrottle

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _redis():
    import redis

    url = os.environ.get("RATELIMIT_REDIS_URL") or os.environ.get(
        "DEDUPE_REDIS_URL", "redis://redis:6379/0"
    )
    return redis.from_url(url, decode_responses=True)


def _parse_rate(rate: str) -> tuple[int, int]:
    """'120/min' -> (120, 60). Supports sec/min/hour/day."""
    count, _, period = rate.partition("/")
    seconds = {"s": 1, "sec": 1, "m": 60, "min": 60, "h": 3600, "hour": 3600, "d": 86400, "day": 86400}
    return int(count), seconds[period]


class UserRateThrottle(BaseThrottle):
    """Fixed-window per-user throttle. Rate from RATELIMIT_USER_RATE (e.g. 120/min)."""

    def allow_request(self, request, view) -> bool:
        if os.environ.get("RATELIMIT_ENABLED", "1") in ("0", "false", "False"):
            return True
        user = getattr(request, "user", None)
        user_id = getattr(user, "user_id", None)
        if not user_id:
            return True

        limit, window = _parse_rate(os.environ.get("RATELIMIT_USER_RATE", "120/min"))
        import time

        bucket = int(time.time()) // window
        key = f"ratelimit:{user_id}:{bucket}"
        try:
            r = _redis()
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            current = pipe.execute()[0]
        except Exception:  # noqa: BLE001
            logger.warning("ratelimit: redis unavailable, allowing", exc_info=True)
            return True
        self._wait = window
        return current <= limit

    def wait(self):  # noqa: D102
        return getattr(self, "_wait", None)
