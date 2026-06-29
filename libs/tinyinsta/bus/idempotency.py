from __future__ import annotations

import os
from typing import Protocol

# Where dedupe keys live. Defaults to a dedicated Redis DB so the dedupe set is
# isolated from any service's own Redis data (keys are namespaced per service, so
# all consumers can safely share this one DB).
DEFAULT_DEDUPE_REDIS_URL = "redis://redis:6379/0"


class DedupeStore(Protocol):
    def seen(self, event_id: str) -> bool: ...
    def mark(self, event_id: str) -> None: ...


class InMemoryDedupeStore:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def seen(self, event_id: str) -> bool:
        return event_id in self._seen

    def mark(self, event_id: str) -> None:
        self._seen.add(event_id)


class RedisDedupeStore:
    def __init__(self, redis_client, service_name: str, ttl_seconds: int = 7 * 24 * 3600):
        self._redis = redis_client
        self._prefix = f"seen:{service_name}:"
        self._ttl = ttl_seconds

    def seen(self, event_id: str) -> bool:
        return bool(self._redis.exists(self._prefix + event_id))

    def mark(self, event_id: str) -> None:
        self._redis.set(self._prefix + event_id, "1", ex=self._ttl)


def redis_dedupe_store(
    service_name: str,
    *,
    url: str | None = None,
    ttl_seconds: int = 7 * 24 * 3600,
) -> RedisDedupeStore:
    """Build a Redis-backed dedupe store for a consumer.

    Durable across restarts and shared across replicas of the same service, so
    at-least-once delivery from the bus doesn't translate into duplicate side
    effects. `service_name` namespaces the keys (typically the consumer group id).
    The Redis URL comes from DEDUPE_REDIS_URL, falling back to a dedicated DB.
    """
    import redis

    url = url or os.environ.get("DEDUPE_REDIS_URL", DEFAULT_DEDUPE_REDIS_URL)
    client = redis.from_url(url, decode_responses=True)
    return RedisDedupeStore(client, service_name, ttl_seconds=ttl_seconds)
