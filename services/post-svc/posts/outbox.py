"""Transactional outbox for post-svc.

The hazard the outbox removes: writing to MongoDB and publishing to the bus are
two systems, so "write then publish" can lose an event if the process dies in
between (post saved, fan-out never happens) — the dual-write problem the
architecture docs flag as a known eventual-consistency pitfall.

Instead, the domain write and the event are committed **in one MongoDB
transaction** (the post and an ``outbox`` row land together or not at all). A
separate relay (``manage.py outbox_relay``) then publishes pending rows to the
bus and marks them sent. The relay re-publishes the persisted ``event_id``, so a
crash mid-relay yields an at-least-once redelivery that downstream consumers
dedupe — never a lost event.

Requires MongoDB transactions → the compose ``mongo`` runs as a single-node
replica set (``rs0``). If transactions are unavailable the helper degrades to a
best-effort sequential write and logs a warning, so dev without a replica set
still functions (without the atomicity guarantee).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from pymongo.errors import OperationFailure

from posts.mongo import get_db

logger = logging.getLogger(__name__)


def outbox_collection():
    return get_db()["outbox"]


def _new_entry(event_type: str, data: dict[str, Any], key: str | None) -> dict:
    return {
        "_id": str(uuid.uuid4()),  # becomes the event_id on publish
        "type": event_type,
        "data": data,
        "key": key,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "published_at": None,
    }


def write_atomically(
    domain_write: Callable[[Any], None],
    events: list[tuple[str, dict[str, Any], str | None]],
) -> None:
    """Run ``domain_write(session)`` and persist ``events`` to the outbox in one
    transaction.

    ``events`` is a list of ``(event_type, data, key)``. ``domain_write`` must
    perform its MongoDB writes using the ``session`` it is handed so they join
    the transaction.
    """
    entries = [_new_entry(t, d, k) for (t, d, k) in events]
    client = get_db().client
    try:
        with client.start_session() as session:
            with session.start_transaction():
                domain_write(session)
                if entries:
                    outbox_collection().insert_many(entries, session=session)
        return
    except OperationFailure as exc:
        # Transactions unsupported (standalone mongo) → degrade. The domain write
        # and the outbox insert are then two steps; the relay still guarantees the
        # event is eventually published, only the cross-write atomicity is lost.
        if "Transaction numbers" in str(exc) or "replica set" in str(exc).lower():
            logger.warning("outbox: transactions unavailable, writing best-effort")
            domain_write(None)
            if entries:
                outbox_collection().insert_many(entries)
            return
        raise


def fetch_pending(limit: int = 100) -> list[dict]:
    return list(
        outbox_collection()
        .find({"status": "pending"})
        .sort("created_at", 1)
        .limit(limit)
    )


def mark_published(entry_id: str) -> None:
    outbox_collection().update_one(
        {"_id": entry_id},
        {"$set": {"status": "published", "published_at": datetime.now(timezone.utc).isoformat()}},
    )
