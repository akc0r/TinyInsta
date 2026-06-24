from django.conf import settings


def get_driver():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


def follow(follower_id: str, followee_id: str) -> None:
    raise NotImplementedError


def unfollow(follower_id: str, followee_id: str) -> None:
    raise NotImplementedError


def suggestions(user_id: str) -> list[dict]:
    raise NotImplementedError
