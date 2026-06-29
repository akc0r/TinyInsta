"""Tests for the fan-out decision in the bus dispatcher (hybrid celebrity path).

These drive the real ``Command`` handlers with real event envelopes, against a
fake Redis. ``fan_out`` / ``back_fill`` / ``purge`` are spied on so we can assert
*which* targets the dispatcher chose — the heart of the hybrid fan-out.
"""

import pytest
from tinyinsta.events import Envelope, types

from timeline import store
from timeline.management.commands.consume import Command


@pytest.fixture
def cmd():
    return Command()


@pytest.fixture
def spy(monkeypatch):
    calls = {"fan_out": [], "back_fill": [], "purge": []}
    monkeypatch.setattr(
        store, "fan_out", lambda targets, post_id, ts: calls["fan_out"].append((sorted(targets), post_id))
    )
    monkeypatch.setattr(
        store, "back_fill", lambda follower, author: calls["back_fill"].append((follower, author))
    )
    monkeypatch.setattr(
        store, "purge", lambda follower, author: calls["purge"].append((follower, author))
    )
    return calls


def _post_created(author_id, post_id="post1"):
    return Envelope(
        type=types.POST_CREATED,
        data={"author_id": author_id, "post_id": post_id, "created_at": 1000.0},
    )


def _followed(follower_id, followee_id):
    return Envelope(
        type=types.USER_FOLLOWED,
        data={"follower_id": follower_id, "followee_id": followee_id},
    )


def test_normal_author_fans_out_to_followers_and_self(redis, spy, cmd):
    store.add_follower("author", "f1")
    store.add_follower("author", "f2")

    cmd._dispatch(_post_created("author"))

    assert spy["fan_out"] == [(["author", "f1", "f2"], "post1")]
    assert not redis.sismember(store.CELEBRITIES_KEY, "author")


def test_celebrity_author_does_not_fan_out_to_followers(
    redis, spy, cmd, small_celebrity_threshold
):
    for i in range(small_celebrity_threshold):
        store.add_follower("celeb", f"f{i}")

    cmd._dispatch(_post_created("celeb"))

    # Hybrid path: pushed only to the author's own home, never to followers.
    assert spy["fan_out"] == [(["celeb"], "post1")]
    assert redis.sismember(store.CELEBRITIES_KEY, "celeb")


def test_follow_back_fills_for_normal_account(redis, spy, cmd):
    cmd._dispatch(_followed("follower", "author"))

    assert spy["back_fill"] == [("follower", "author")]
    # The local social-graph projection is updated from the event.
    assert "follower" in set(store.followers_of("author"))


def test_follow_a_celebrity_skips_back_fill(redis, spy, cmd, small_celebrity_threshold):
    # Pre-load the celebrity with enough followers to already be over the line.
    for i in range(small_celebrity_threshold):
        store.add_follower("celeb", f"existing{i}")

    cmd._dispatch(_followed("newcomer", "celeb"))

    # A celebrity's posts are pulled at read time, so back-fill is skipped and
    # the account is (re)marked as a celebrity.
    assert spy["back_fill"] == []
    assert redis.sismember(store.CELEBRITIES_KEY, "celeb")


def test_unfollow_purges_author_posts(redis, spy, cmd):
    envelope = Envelope(
        type=types.USER_UNFOLLOWED,
        data={"follower_id": "follower", "followee_id": "author"},
    )
    cmd._dispatch(envelope)

    assert spy["purge"] == [("follower", "author")]
