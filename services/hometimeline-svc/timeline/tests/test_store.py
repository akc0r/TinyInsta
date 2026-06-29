"""Unit tests for the home-timeline store (Redis read model + fan-out)."""

import pytest

from timeline import store


def test_follower_projection_round_trips(redis):
    store.add_follower("author", "f1")
    store.add_follower("author", "f2")
    assert set(store.followers_of("author")) == {"f1", "f2"}

    store.remove_follower("author", "f1")
    assert set(store.followers_of("author")) == {"f2"}


def test_is_celebrity_crosses_threshold(redis, small_celebrity_threshold):
    for i in range(small_celebrity_threshold - 1):
        store.add_follower("author", f"f{i}")
    assert store.is_celebrity("author") is False

    store.add_follower("author", "one-more")
    assert store.is_celebrity("author") is True


def test_fan_out_pushes_newest_first(redis):
    store.fan_out(["u1"], "postA", ts=100.0)
    store.fan_out(["u1"], "postB", ts=200.0)

    page = store.page("u1", cursor=None)
    assert page["items"] == ["postB", "postA"]


def test_fan_out_is_capped_to_max_home(redis, monkeypatch):
    monkeypatch.setattr(store, "MAX_HOME", 3)
    for i in range(5):
        store.fan_out(["u1"], f"post{i}", ts=float(i))

    page = store.page("u1", cursor=None, limit=10)
    # Only the 3 newest survive the trim; the two oldest are dropped.
    assert page["items"] == ["post4", "post3", "post2"]


def test_page_pagination_excludes_cursor(redis):
    for i in range(3):
        store.fan_out(["u1"], f"post{i}", ts=float(i))

    first = store.page("u1", cursor=None, limit=2)
    assert first["items"] == ["post2", "post1"]
    assert first["next_cursor"] == 1.0

    second = store.page("u1", cursor=str(first["next_cursor"]), limit=2)
    assert second["items"] == ["post0"]
    assert second["next_cursor"] is None


def test_remove_post_drops_from_every_timeline(redis):
    store.fan_out(["u1", "u2"], "postA", ts=1.0)
    store.remove_post(["u1", "u2"], "postA")

    assert store.page("u1", cursor=None)["items"] == []
    assert store.page("u2", cursor=None)["items"] == []


def test_back_fill_pulls_author_posts_with_original_scores(redis, usertimeline):
    usertimeline["author"] = [("p2", 200.0), ("p1", 100.0)]
    store.back_fill("follower", "author")

    # Back-filled posts land at their original timestamps, newest first.
    assert store.page("follower", cursor=None)["items"] == ["p2", "p1"]


def test_purge_removes_unfollowed_author_posts(redis, usertimeline):
    usertimeline["author"] = [("p1", 100.0), ("p2", 200.0)]
    store.back_fill("follower", "author")
    store.purge("follower", "author")

    assert store.page("follower", cursor=None)["items"] == []


@pytest.mark.parametrize("limit,expected", [(1, ["b"]), (5, ["b", "a"])])
def test_page_respects_limit(redis, limit, expected):
    store.fan_out(["u1"], "a", ts=1.0)
    store.fan_out(["u1"], "b", ts=2.0)
    assert store.page("u1", cursor=None, limit=limit)["items"] == expected
