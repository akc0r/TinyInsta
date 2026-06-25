from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UserCreated:
    user_id: str
    username: str


@dataclass(slots=True)
class UserFollowed:
    follower_id: str
    followee_id: str


@dataclass(slots=True)
class UserUnfollowed:
    follower_id: str
    followee_id: str


@dataclass(slots=True)
class PostCreated:
    post_id: str
    author_id: str
    created_at: str
    caption: str = ""
    hashtags: tuple[str, ...] = ()


@dataclass(slots=True)
class PostCommented:
    post_id: str
    comment_id: str
    author_id: str  # the commenter
    # The post owner, carried so realtime-svc can target a "comment" notification
    # without a sync call back to post-svc (it is the only one that knows the owner).
    post_author_id: str = ""
    body: str = ""
    created_at: str = ""


@dataclass(slots=True)
class PostDeleted:
    post_id: str
    author_id: str


@dataclass(slots=True)
class PostLiked:
    post_id: str
    user_id: str
    new_count: int


@dataclass(slots=True)
class PostUnliked:
    post_id: str
    user_id: str
    new_count: int


@dataclass(slots=True)
class MediaUploaded:
    media_id: str
    kind: str
    original_url: str


@dataclass(slots=True)
class MediaProcessed:
    media_id: str
    variants: dict


@dataclass(slots=True)
class StoryCreated:
    story_id: str
    author_id: str


@dataclass(slots=True)
class StoryViewed:
    story_id: str
    viewer_id: str
