"""Contract registry for bus events.

Every event ``type`` is mapped to its payload dataclass (the contract). The
producer validates a payload against the registered schema *before* it goes on
the wire, and the consumer can validate on the way in — so a contract breach is
caught at the boundary instead of corrupting a downstream read model.

This is the lightweight, in-process form of a Schema Registry: the schemas live
in code and are validated structurally (required fields present, no unknown
fields, JSON-serialisable types). The binary-Avro upgrade — registering these
same schemas in a Confluent/Redpanda Schema Registry and serialising the
``data`` block as Avro instead of JSON — is a drop-in evolution of this module
(see ``docs/EVENTS.md``); the contract source of truth stays here either way.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from tinyinsta.events import schemas, types


class ContractError(ValueError):
    """Raised when an event payload does not match its registered schema."""


# type string -> payload dataclass. The single source of truth for who carries
# what; mirrored in docs/EVENTS.md.
REGISTRY: dict[str, type] = {
    types.USER_CREATED: schemas.UserCreated,
    types.USER_FOLLOWED: schemas.UserFollowed,
    types.USER_UNFOLLOWED: schemas.UserUnfollowed,
    types.USER_BLOCKED: schemas.UserBlocked,
    types.USER_UNBLOCKED: schemas.UserUnblocked,
    types.USER_CLOSE_FRIEND_ADDED: schemas.UserCloseFriendAdded,
    types.USER_CLOSE_FRIEND_REMOVED: schemas.UserCloseFriendRemoved,
    types.USER_MENTIONED: schemas.UserMentioned,
    types.POST_CREATED: schemas.PostCreated,
    types.POST_COMMENTED: schemas.PostCommented,
    types.POST_COMMENT_EDITED: schemas.PostCommentEdited,
    types.POST_COMMENT_DELETED: schemas.PostCommentDeleted,
    types.POST_DELETED: schemas.PostDeleted,
    types.POST_LIKED: schemas.PostLiked,
    types.POST_UNLIKED: schemas.PostUnliked,
    types.POST_SAVED: schemas.PostSaved,
    types.POST_UNSAVED: schemas.PostUnsaved,
    types.POST_REPOSTED: schemas.PostReposted,
    types.POST_UNREPOSTED: schemas.PostUnreposted,
    types.MEDIA_UPLOADED: schemas.MediaUploaded,
    types.MEDIA_PROCESSED: schemas.MediaProcessed,
    types.STORY_CREATED: schemas.StoryCreated,
    types.STORY_VIEWED: schemas.StoryViewed,
    types.MESSAGE_SENT: schemas.MessageSent,
}


def schema_for(event_type: str) -> type | None:
    return REGISTRY.get(event_type)


def assert_complete() -> None:
    """Fail if the catalog (``types.ALL``) and the schema registry diverge.

    Run in CI as a build-time contract gate: a new event type that ships without
    a registered payload schema (or vice versa) breaks the build instead of only
    surfacing at runtime when something publishes it.
    """
    declared = set(types.ALL)
    registered = set(REGISTRY)
    missing_schema = declared - registered
    orphan_schema = registered - declared
    problems = []
    if missing_schema:
        problems.append(f"types without a schema: {sorted(missing_schema)}")
    if orphan_schema:
        problems.append(f"schemas without a declared type: {sorted(orphan_schema)}")
    if problems:
        raise ContractError("; ".join(problems))


def _required_fields(schema: type) -> set[str]:
    return {
        f.name
        for f in dataclasses.fields(schema)
        if f.default is dataclasses.MISSING
        and f.default_factory is dataclasses.MISSING  # type: ignore[misc]
    }


def _known_fields(schema: type) -> set[str]:
    return {f.name for f in dataclasses.fields(schema)}


def validate(event_type: str, data: dict[str, Any]) -> None:
    """Validate ``data`` against the schema registered for ``event_type``.

    Raises ``ContractError`` on an unknown type, a missing required field, or an
    unexpected field. Unknown types are rejected so a typo in a producer can't
    silently publish an event no consumer will ever recognise.
    """
    schema = REGISTRY.get(event_type)
    if schema is None:
        raise ContractError(f"unknown event type: {event_type!r}")
    if not isinstance(data, dict):
        raise ContractError(f"{event_type}: payload must be a dict, got {type(data).__name__}")

    keys = set(data)
    missing = _required_fields(schema) - keys
    if missing:
        raise ContractError(f"{event_type}: missing required field(s): {sorted(missing)}")
    unknown = keys - _known_fields(schema)
    if unknown:
        raise ContractError(f"{event_type}: unknown field(s): {sorted(unknown)}")
