"""Per-user rate limiting (anti-abuse), shared across services.

Traefik already rate-limits per client IP at the gateway; this adds a per-**user**
limit so one authenticated account can't hammer the API from many IPs (or behind
a NAT where IP limiting is too coarse). It is a Redis fixed-window counter keyed
by the Keycloak user id, so the limit holds across service replicas.

Fail-open: if Redis is unreachable the request is allowed rather than the API
going dark on a cache blip — availability over a best-effort abuse control.
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
            return True  # unauthenticated endpoints (docs/health) — IP limiting covers these

        limit, window = _parse_rate(os.environ.get("RATELIMIT_USER_RATE", "120/min"))
        # Bucket key rotates with the window so the counter resets automatically.
        import time

        bucket = int(time.time()) // window
        key = f"ratelimit:{user_id}:{bucket}"
        try:
            r = _redis()
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            current = pipe.execute()[0]
        except Exception:  # noqa: BLE001 — fail-open on Redis trouble
            logger.warning("ratelimit: redis unavailable, allowing", exc_info=True)
            return True
        self._wait = window
        return current <= limit

    def wait(self):  # noqa: D102 — DRF asks how long until retry
        return getattr(self, "_wait", None)
