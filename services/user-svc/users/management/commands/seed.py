"""Seed a large social graph to demo the read-model fan-out at scale.

Creates N profiles (the user-svc system of record: Postgres + Neo4j) plus one
**celebrity** that *everyone* follows, and publishes the matching events
(`user.created`, `user.followed`, a few `post.created`) so every downstream read
model — hometimeline, usertimeline, search — converges on its own, exactly as it
would in production. No cross-service database is written directly.

This is what exercises the hybrid/celebrity path in hometimeline-svc: once the
celebrity crosses ``CELEBRITY_FOLLOWER_THRESHOLD`` followers, its posts stop
being fanned out on write and are pulled at read time instead.

Notes
- Seeded users are NOT created in Keycloak, so they cannot log in — this is a
  data set to demonstrate read-model scaling, not interactive accounts.
- Run against an empty system (``make clean`` first) to avoid username clashes.
- Seeding is eventually consistent: with the app's consumers running, they chew
  through the published events in the background over a short while.

    python manage.py seed --users 10000 --follows-per-user 10
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand
from tinyinsta.bus import Producer
from tinyinsta.events import types

from users import graph
from users.models import Profile


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


class Command(BaseCommand):
    help = "Seed N profiles + a follow graph + 1 celebrity, publishing the events."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=10000)
        parser.add_argument(
            "--follows-per-user",
            type=int,
            default=10,
            help="random followees per user, on top of the celebrity",
        )
        parser.add_argument("--celebrity-posts", type=int, default=5)
        parser.add_argument(
            "--normal-posts",
            type=int,
            default=500,
            help="posts emitted by random normal users, to fill home feeds",
        )
        parser.add_argument("--prefix", default="seed")
        parser.add_argument("--batch", type=int, default=1000)

    def handle(self, *args, **opts):
        n = opts["users"]
        prefix = opts["prefix"]
        batch = opts["batch"]
        producer = Producer()

        threshold = self._threshold()
        if n < threshold:
            self.stdout.write(
                self.style.WARNING(
                    f"--users {n} < celebrity threshold {threshold}: the celebrity "
                    "won't be promoted; raise --users or lower the threshold."
                )
            )

        # --- 1. Identities -----------------------------------------------------
        celeb_id = str(uuid.uuid4())
        user_ids = [str(uuid.uuid4()) for _ in range(n)]
        self.stdout.write(f"Seeding {n} users + 1 celebrity…")

        # --- 2. Profiles (Postgres, user-svc's own store) ---------------------
        profiles = [
            Profile(user_id=celeb_id, username=f"{prefix}_celebrity", name="The Celebrity")
        ]
        profiles += [
            Profile(user_id=uid, username=f"{prefix}_user{i}", name=f"User {i}")
            for i, uid in enumerate(user_ids)
        ]
        Profile.objects.bulk_create(profiles, batch_size=batch, ignore_conflicts=True)

        # --- 3. Graph nodes + edges (Neo4j, user-svc's own store) -------------
        for chunk in _chunks([celeb_id] + user_ids, batch):
            graph.bulk_ensure_users(chunk)

        edges: list[tuple[str, str]] = [(uid, celeb_id) for uid in user_ids]
        fpu = opts["follows_per_user"]
        if fpu > 0 and n > 1:
            for uid in user_ids:
                for followee in random.sample(user_ids, min(fpu, n - 1)):
                    if followee != uid:
                        edges.append((uid, followee))
        for chunk in _chunks(edges, batch * 5):
            graph.bulk_follow(chunk)
        self.stdout.write(f"  graph: {len(edges)} follow edges")

        # --- 4. Publish events so the read models converge --------------------
        publish = self._publisher(producer)
        for p in profiles:
            publish(types.USER_CREATED, {"user_id": str(p.user_id), "username": p.username},
                    key=str(p.user_id))
        for follower_id, followee_id in edges:
            publish(types.USER_FOLLOWED,
                    {"follower_id": follower_id, "followee_id": followee_id},
                    key=follower_id)
        self._emit_posts(publish, celeb_id, user_ids, opts)

        producer.flush()
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {len(profiles)} profiles, {len(edges)} follows. "
            "Consumers will converge in the background."
        ))

    # --- helpers -------------------------------------------------------------
    def _threshold(self) -> int:
        from django.conf import settings

        return int(getattr(settings, "CELEBRITY_FOLLOWER_THRESHOLD", 5000) or 5000)

    def _publisher(self, producer):
        count = {"n": 0}

        def publish(event_type, data, key):
            producer.publish(event_type, data, key=key)
            count["n"] += 1
            # Bound the producer's buffer on big seeds.
            if count["n"] % 5000 == 0:
                producer.flush()
                self.stdout.write(f"  published {count['n']} events…")

        return publish

    def _emit_posts(self, publish, celeb_id, user_ids, opts):
        now = datetime.now(timezone.utc)

        def post(author_id, age_seconds, caption):
            created = (now - timedelta(seconds=age_seconds)).isoformat()
            publish(
                types.POST_CREATED,
                {
                    "post_id": str(uuid.uuid4()),
                    "author_id": author_id,
                    "created_at": created,
                    "caption": caption,
                    "hashtags": [],
                },
                key=author_id,
            )

        for i in range(opts["celebrity_posts"]):
            post(celeb_id, i * 60, f"Celebrity post #{i}")
        for i in range(opts["normal_posts"]):
            post(random.choice(user_ids), random.randint(0, 86400), f"Post #{i}")
