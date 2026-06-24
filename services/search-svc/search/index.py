from functools import lru_cache

from django.conf import settings

INDEX_USERS = "users"
INDEX_POSTS = "posts"


@lru_cache(maxsize=1)
def get_client():
    from elasticsearch import Elasticsearch

    return Elasticsearch(settings.ELASTICSEARCH_URL)


def index_user(user_id: str, username: str, bio: str = "") -> None:
    raise NotImplementedError


def index_post(post: dict) -> None:
    raise NotImplementedError


def remove_post(post_id: str) -> None:
    raise NotImplementedError
