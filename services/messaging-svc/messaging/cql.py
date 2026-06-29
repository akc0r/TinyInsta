"""Cassandra access for direct messages.

Why Cassandra here: direct messages are the canonical Cassandra workload —
write-heavy, append-only, time-ordered, and naturally partitioned by
conversation. The data model is **query-first** (one table per read pattern), the
opposite of a normalised relational schema:

- ``messages_by_conversation`` — partition = conversation, clustering by a
  ``timeuuid`` DESC, so reading a conversation's latest messages (and paging
  older ones) is a single sequential partition read.
- ``conversations_by_user`` — partition = user, one row per conversation, so a
  user's inbox is one partition read. Ordered client-side (a user has few
  conversations) to avoid the delete+insert dance of mutating a clustering key.

The keyspace/tables are created idempotently at startup (``IF NOT EXISTS``).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _cluster_session():
    from cassandra.cluster import Cluster

    cluster = Cluster(settings.CASSANDRA_HOSTS, port=settings.CASSANDRA_PORT)
    session = cluster.connect()
    _ensure_schema(session)
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    return session


def session():
    return _cluster_session()


def _ensure_schema(s) -> None:
    ks = settings.CASSANDRA_KEYSPACE
    s.execute(
        f"""CREATE KEYSPACE IF NOT EXISTS {ks}
            WITH replication = {{'class':'SimpleStrategy','replication_factor':{settings.CASSANDRA_REPLICATION}}}"""
    )
    s.execute(
        f"""CREATE TABLE IF NOT EXISTS {ks}.messages_by_conversation (
                conversation_id text,
                message_id timeuuid,
                sender_id text,
                recipient_id text,
                body text,
                created_at timestamp,
                PRIMARY KEY ((conversation_id), message_id)
            ) WITH CLUSTERING ORDER BY (message_id DESC)"""
    )
    s.execute(
        f"""CREATE TABLE IF NOT EXISTS {ks}.conversations_by_user (
                user_id text,
                conversation_id text,
                peer_id text,
                last_message text,
                last_message_at timestamp,
                PRIMARY KEY ((user_id), conversation_id)
            )"""
    )


def conversation_id_for(a: str, b: str) -> str:
    """Deterministic id for a 1:1 conversation: stable regardless of who sends."""
    return ":".join(sorted([a, b]))


def send_message(sender_id: str, recipient_id: str, body: str) -> dict:
    s = session()
    conv_id = conversation_id_for(sender_id, recipient_id)
    msg_id = uuid.uuid1()  # timeuuid: time-ordered + unique
    now = datetime.now(timezone.utc)

    s.execute(
        """INSERT INTO messages_by_conversation
           (conversation_id, message_id, sender_id, recipient_id, body, created_at)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (conv_id, msg_id, sender_id, recipient_id, body, now),
    )
    # Upsert the conversation row for both participants (inbox views).
    for owner, peer in ((sender_id, recipient_id), (recipient_id, sender_id)):
        s.execute(
            """INSERT INTO conversations_by_user
               (user_id, conversation_id, peer_id, last_message, last_message_at)
               VALUES (%s, %s, %s, %s, %s)""",
            (owner, conv_id, peer, body, now),
        )
    return {
        "message_id": str(msg_id),
        "conversation_id": conv_id,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "body": body,
        "created_at": now.isoformat(),
    }


def list_conversations(user_id: str) -> list[dict]:
    rows = session().execute(
        "SELECT conversation_id, peer_id, last_message, last_message_at "
        "FROM conversations_by_user WHERE user_id = %s",
        (user_id,),
    )
    convs = [
        {
            "conversation_id": r.conversation_id,
            "peer_id": r.peer_id,
            "last_message": r.last_message,
            "last_message_at": r.last_message_at.isoformat() if r.last_message_at else None,
        }
        for r in rows
    ]
    convs.sort(key=lambda c: c["last_message_at"] or "", reverse=True)
    return convs


def list_messages(conversation_id: str, cursor: str | None, limit: int) -> dict:
    """Newest-first page of a conversation. `cursor` is the message_id of the last
    item from the previous page; older messages are returned (clustering DESC)."""
    s = session()
    if cursor:
        rows = list(
            s.execute(
                "SELECT message_id, sender_id, recipient_id, body, created_at "
                "FROM messages_by_conversation WHERE conversation_id = %s AND message_id < %s LIMIT %s",
                (conversation_id, uuid.UUID(cursor), limit),
            )
        )
    else:
        rows = list(
            s.execute(
                "SELECT message_id, sender_id, recipient_id, body, created_at "
                "FROM messages_by_conversation WHERE conversation_id = %s LIMIT %s",
                (conversation_id, limit),
            )
        )
    items = [
        {
            "message_id": str(r.message_id),
            "sender_id": r.sender_id,
            "recipient_id": r.recipient_id,
            "body": r.body,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    next_cursor = items[-1]["message_id"] if len(items) == limit else None
    return {"items": items, "next_cursor": next_cursor}
