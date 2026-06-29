"""Shared fixtures for the hometimeline-svc fan-out tests.

The store talks to Redis and the back-fill path calls usertimeline-svc over HTTP.
Both are swapped for in-process fakes so the fan-out logic can be exercised
without any running infrastructure.
"""

import fakeredis
import pytest

from timeline import store


@pytest.fixture
def redis(monkeypatch):
    """Back the store with an in-memory Redis (fakeredis) for the test."""
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(store, "get_redis", lambda: client)
    return client


@pytest.fixture
def usertimeline(monkeypatch):
    """Stub usertimeline-svc reads (back-fill / purge / celebrity pull).

    Returns a dict mapping author_id -> list[(post_id, score)]; mutate it in a
    test to control what the per-author read model "contains".
    """
    posts: dict[str, list[tuple[str, float]]] = {}

    def recent_posts(author_id, limit=30):
        return list(posts.get(author_id, []))[:limit]

    monkeypatch.setattr("timeline.clients.recent_posts", recent_posts)
    return posts


@pytest.fixture
def small_celebrity_threshold(settings):
    """Lower the celebrity cutoff so tests don't need thousands of followers."""
    settings.CELEBRITY_FOLLOWER_THRESHOLD = 3
    return settings.CELEBRITY_FOLLOWER_THRESHOLD
