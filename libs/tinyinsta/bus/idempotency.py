from __future__ import annotations

from typing import Protocol


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
