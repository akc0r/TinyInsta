"""End-to-end fan-out flow, driven entirely through real event envelopes.

No mocks of the logic under test: events go through the real ``Command``
dispatcher, mutate the real store (fake Redis), and are read back through both
``store.page`` and the real DRF ``HomeTimeline`` view. Only the infra edges
(Redis, the usertimeline-svc HTTP read) are faked.

Covers the two paths that matter:
  1. normal account  → fan-out-on-write, follower sees the post (+ back-fill);
  2. celebrity account → no fan-out, follower still sees the post via the
     read-time pull (the hybrid path).
"""

from types import SimpleNamespace

import pytest
from tinyinsta.events import Envelope, types

from timeline import store
from timeline.management.commands.consume import Command
from timeline.views import HomeTimeline


@pytest.fixture
def cmd():
    return Command()


def _feed(cmd, event_type, data):
    cmd._dispatch(Envelope(type=event_type, data=data))


def _store_items(user_id):
    return store.page(user_id, cursor=None, limit=50)["items"]


def _read_via_view(user_id):
    """Exercise the real read path through the DRF view (no auth plumbing)."""
    request = SimpleNamespace(
        query_params={}, user=SimpleNamespace(user_id=user_id)
    )
    return HomeTimeline().get(request).data


def test_normal_account_end_to_end(redis, usertimeline, cmd):
    # The author already has one older post in their per-author read model.
    usertimeline["author"] = [("old", 100.0)]

    # A user follows the author → back-fill pulls the older post in.
    _feed(cmd, types.USER_FOLLOWED, {"follower_id": "alice", "followee_id": "author"})
    assert _store_items("alice") == ["old"]

    # The author publishes a new post → fan-out-on-write reaches the follower.
    _feed(
        cmd,
        types.POST_CREATED,
        {"author_id": "author", "post_id": "fresh", "created_at": 200.0},
    )

    # The follower's home now has both, newest first — via store and via the view.
    assert _store_items("alice") == ["fresh", "old"]
    assert _read_via_view("alice")["items"] == ["fresh", "old"]

    # Deleting the post removes it from the follower's timeline.
    _feed(
        cmd,
        types.POST_DELETED,
        {"author_id": "author", "post_id": "fresh"},
    )
    assert _store_items("alice") == ["old"]


def test_celebrity_account_end_to_end(redis, usertimeline, cmd, small_celebrity_threshold):
    # Enough followers subscribe to push the author over the celebrity line.
    followers = [f"fan{i}" for i in range(small_celebrity_threshold)]
    for fan in followers:
        _feed(cmd, types.USER_FOLLOWED, {"follower_id": fan, "followee_id": "celeb"})

    # The celebrity publishes a post. usertimeline-svc would also record it; we
    # mirror that into the fake so the read-time pull can find it.
    _feed(
        cmd,
        types.POST_CREATED,
        {"author_id": "celeb", "post_id": "viral", "created_at": 500.0},
    )
    usertimeline["celeb"] = [("viral", 500.0)]

    last_fan = followers[-1]
    # Hybrid path: the post was NOT pushed into the follower's stored timeline...
    assert redis.zcard(f"home:{last_fan}") == 0
    # ...yet the follower still sees it, merged in at read time from the pull.
    assert _read_via_view(last_fan)["items"] == ["viral"]

