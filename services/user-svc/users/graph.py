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
    turn follow the candidate). Excludes the user themselves and anyone already
    followed.
    """
    rows = _run(
        """
        MATCH (me:User {user_id: $user_id})-[:FOLLOWS]->(:User)-[:FOLLOWS]->(fof:User)
        WHERE fof.user_id <> $user_id
          AND NOT EXISTS { (me)-[:FOLLOWS]->(fof) }
        RETURN fof.user_id AS user_id, count(*) AS mutual
        ORDER BY mutual DESC, fof.user_id
        LIMIT $limit
        """,
        user_id=user_id,
        limit=limit,
    )
    return [{"user_id": r["user_id"], "mutual": r["mutual"]} for r in rows]
