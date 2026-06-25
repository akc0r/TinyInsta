"""Social graph backed by Neo4j.

Nodes are `(:User {user_id})`; relationships are `(:User)-[:FOLLOWS {since}]->(:User)`.
Postgres stays authoritative for user existence (the profile rows); Neo4j is
authoritative for relationships. Profile hydration (username, avatar, …) is done
by the views from Postgres — this module only ever deals in `user_id`s.
"""

from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_driver():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


def _run(query: str, **params):
    with get_driver().session() as session:
        return list(session.run(query, **params))


def ensure_user(user_id: str) -> None:
    """Make sure a User node exists (called when a profile is provisioned)."""
    _run("MERGE (:User {user_id: $user_id})", user_id=user_id)


def follow(follower_id: str, followee_id: str) -> None:
    _run(
        """
        MERGE (a:User {user_id: $follower})
        MERGE (b:User {user_id: $followee})
        MERGE (a)-[r:FOLLOWS]->(b)
          ON CREATE SET r.since = datetime()
        """,
        follower=follower_id,
        followee=followee_id,
    )


def unfollow(follower_id: str, followee_id: str) -> None:
    _run(
        """
        MATCH (:User {user_id: $follower})-[r:FOLLOWS]->(:User {user_id: $followee})
        DELETE r
        """,
        follower=follower_id,
        followee=followee_id,
    )


def following_ids(user_id: str) -> list[str]:
    rows = _run(
        """
        MATCH (:User {user_id: $user_id})-[:FOLLOWS]->(b:User)
        RETURN b.user_id AS user_id
        """,
        user_id=user_id,
    )
    return [r["user_id"] for r in rows]


def follower_ids(user_id: str) -> list[str]:
    rows = _run(
        """
        MATCH (a:User)-[:FOLLOWS]->(:User {user_id: $user_id})
        RETURN a.user_id AS user_id
        """,
        user_id=user_id,
    )
    return [r["user_id"] for r in rows]


def counts(user_id: str) -> dict:
    """Followers / following counts for a single user (0/0 if unknown)."""
    rows = _run(
        """
        RETURN COUNT { (:User {user_id: $user_id})-[:FOLLOWS]->() } AS following,
               COUNT { ()-[:FOLLOWS]->(:User {user_id: $user_id}) } AS followers
        """,
        user_id=user_id,
    )
    row = rows[0]
    return {"followers": row["followers"], "following": row["following"]}


def is_following(follower_id: str, followee_id: str) -> bool:
    rows = _run(
        """
        RETURN EXISTS {
          (:User {user_id: $follower})-[:FOLLOWS]->(:User {user_id: $followee})
        } AS following
        """,
        follower=follower_id,
        followee=followee_id,
    )
    return bool(rows[0]["following"])


def suggestions(user_id: str, limit: int = 10) -> list[dict]:
    """Friends-of-friends (2nd degree) the user does not already follow.

    Ranked by the number of mutual connections (people the user follows who in
    turn follow the candidate). Excludes the user themselves, anyone already
    followed, and anyone in a block relationship with the user (either way).
    """
    rows = _run(
        """
        MATCH (me:User {user_id: $user_id})-[:FOLLOWS]->(:User)-[:FOLLOWS]->(fof:User)
        WHERE fof.user_id <> $user_id
          AND NOT EXISTS { (me)-[:FOLLOWS]->(fof) }
          AND NOT EXISTS { (me)-[:BLOCKS]-(fof) }
        RETURN fof.user_id AS user_id, count(*) AS mutual
        ORDER BY mutual DESC, fof.user_id
        LIMIT $limit
        """,
        user_id=user_id,
        limit=limit,
    )
    return [{"user_id": r["user_id"], "mutual": r["mutual"]} for r in rows]


# --- Blocking ---------------------------------------------------------------
# (:User)-[:BLOCKS {since}]->(:User). Blocking is the social graph's job, so it
# lives here. Blocking severs any FOLLOWS and CLOSE_FRIEND edges in both
# directions (Instagram semantics) — the caller emits the resulting
# user.unfollowed / user.close_friend_removed events so the read models
# (home/story feeds) converge without reading this database.
def block(blocker_id: str, blocked_id: str) -> dict:
    """Create a BLOCKS edge and tear down any follow / close-friend edges.

    Returns which edges existed (so the view can emit the matching events):
    `a_followed_b`, `b_followed_a`, `a_close_b`, `b_close_a`.
    """
    rows = _run(
        """
        MERGE (a:User {user_id: $blocker})
        MERGE (b:User {user_id: $blocked})
        WITH a, b
        OPTIONAL MATCH (a)-[f1:FOLLOWS]->(b)
        OPTIONAL MATCH (b)-[f2:FOLLOWS]->(a)
        OPTIONAL MATCH (a)-[c1:CLOSE_FRIEND]->(b)
        OPTIONAL MATCH (b)-[c2:CLOSE_FRIEND]->(a)
        WITH a, b,
             f1 IS NOT NULL AS a_followed_b, f2 IS NOT NULL AS b_followed_a,
             c1 IS NOT NULL AS a_close_b, c2 IS NOT NULL AS b_close_a,
             f1, f2, c1, c2
        DELETE f1, f2, c1, c2
        MERGE (a)-[r:BLOCKS]->(b)
          ON CREATE SET r.since = datetime()
        RETURN a_followed_b, b_followed_a, a_close_b, b_close_a
        """,
        blocker=blocker_id,
        blocked=blocked_id,
    )
    row = rows[0]
    return {
        "a_followed_b": bool(row["a_followed_b"]),
        "b_followed_a": bool(row["b_followed_a"]),
        "a_close_b": bool(row["a_close_b"]),
        "b_close_a": bool(row["b_close_a"]),
    }


def unblock(blocker_id: str, blocked_id: str) -> None:
    _run(
        """
        MATCH (:User {user_id: $blocker})-[r:BLOCKS]->(:User {user_id: $blocked})
        DELETE r
        """,
        blocker=blocker_id,
        blocked=blocked_id,
    )


def is_blocking(blocker_id: str, blocked_id: str) -> bool:
    rows = _run(
        """
        RETURN EXISTS {
          (:User {user_id: $blocker})-[:BLOCKS]->(:User {user_id: $blocked})
        } AS blocking
        """,
        blocker=blocker_id,
        blocked=blocked_id,
    )
    return bool(rows[0]["blocking"])


def blocks_either(a_id: str, b_id: str) -> bool:
    """True if either user blocks the other (used to forbid following)."""
    rows = _run(
        """
        RETURN EXISTS {
          (:User {user_id: $a})-[:BLOCKS]-(:User {user_id: $b})
        } AS blocked
        """,
        a=a_id,
        b=b_id,
    )
    return bool(rows[0]["blocked"])


# --- Close friends ----------------------------------------------------------
# (:User)-[:CLOSE_FRIEND]->(:User): a per-owner subset for restricted-audience
# stories. Directed and private to the owner.
def add_close_friend(owner_id: str, friend_id: str) -> None:
    _run(
        """
        MERGE (a:User {user_id: $owner})
        MERGE (b:User {user_id: $friend})
        MERGE (a)-[r:CLOSE_FRIEND]->(b)
          ON CREATE SET r.since = datetime()
        """,
        owner=owner_id,
        friend=friend_id,
    )


def remove_close_friend(owner_id: str, friend_id: str) -> None:
    _run(
        """
        MATCH (:User {user_id: $owner})-[r:CLOSE_FRIEND]->(:User {user_id: $friend})
        DELETE r
        """,
        owner=owner_id,
        friend=friend_id,
    )


def is_close_friend(owner_id: str, friend_id: str) -> bool:
    rows = _run(
        """
        RETURN EXISTS {
          (:User {user_id: $owner})-[:CLOSE_FRIEND]->(:User {user_id: $friend})
        } AS close
        """,
        owner=owner_id,
        friend=friend_id,
    )
    return bool(rows[0]["close"])


def close_friend_ids(owner_id: str) -> list[str]:
    rows = _run(
        """
        MATCH (:User {user_id: $owner})-[:CLOSE_FRIEND]->(b:User)
        RETURN b.user_id AS user_id
        """,
        owner=owner_id,
    )
    return [r["user_id"] for r in rows]
