"""Elasticsearch access layer for the search read model.

Two indices, both **rebuildable** from the bus (no direct user writes):

    users:  { username, bio }                                  (doc _id = user_id)
    posts:  { author_id, caption, hashtags[], created_at }      (doc _id = post_id)

`username` and `hashtags` carry an edge-ngram analyzer so the search bar can do
prefix autocomplete ("jul" -> "julien") without a trailing wildcard query.
"""

from functools import lru_cache

from django.conf import settings

INDEX_USERS = "users"
INDEX_POSTS = "posts"

# Shared analysis: edge n-grams at index time, plain lowercase at search time.
# (n-gramming the query too would match "jul" against any word *containing*
# "jul"; we only want prefixes, so the search analyzer just lowercases.)
_ANALYSIS = {
    "analyzer": {
        "autocomplete_index": {
            "tokenizer": "autocomplete_tokenizer",
            "filter": ["lowercase"],
        },
        "autocomplete_search": {
            "tokenizer": "standard",
            "filter": ["lowercase"],
        },
    },
    "tokenizer": {
        "autocomplete_tokenizer": {
            "type": "edge_ngram",
            "min_gram": 1,
            "max_gram": 20,
            "token_chars": ["letter", "digit"],
        }
    },
}

_USERS_MAPPING = {
    "settings": {"analysis": _ANALYSIS},
    "mappings": {
        "properties": {
            "username": {
                "type": "text",
                "analyzer": "autocomplete_index",
                "search_analyzer": "autocomplete_search",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "bio": {"type": "text"},
        }
    },
}

_POSTS_MAPPING = {
    "settings": {"analysis": _ANALYSIS},
    "mappings": {
        "properties": {
            "author_id": {"type": "keyword"},
            "caption": {"type": "text"},
            # `hashtags` is a keyword for exact /hashtags/{tag} lookups, with an
            # analyzed sub-field for prefix autocomplete in the search bar.
            "hashtags": {
                "type": "keyword",
                "fields": {
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete_index",
                        "search_analyzer": "autocomplete_search",
                    }
                },
            },
            "created_at": {"type": "date"},
        }
    },
}


@lru_cache(maxsize=1)
def get_client():
    from elasticsearch import Elasticsearch

    return Elasticsearch(settings.ELASTICSEARCH_URL)


@lru_cache(maxsize=1)
def ensure_indices() -> None:
    """Create the indices if they are missing. Idempotent; runs once per process.

    Called lazily before any read or write so the service works whether the
    worker or an HTTP request touches Elasticsearch first. lru_cache does not
    cache exceptions, so a transient ES outage is retried on the next call.
    """
    es = get_client()
    if not es.indices.exists(index=INDEX_USERS):
        es.indices.create(index=INDEX_USERS, **_USERS_MAPPING)
    if not es.indices.exists(index=INDEX_POSTS):
        es.indices.create(index=INDEX_POSTS, **_POSTS_MAPPING)


# --- Projections (event handlers) ------------------------------------------

def index_user(user_id: str, username: str, bio: str = "") -> None:
    ensure_indices()
    get_client().index(
        index=INDEX_USERS,
        id=str(user_id),
        document={"username": username, "bio": bio},
    )


def index_post(post: dict) -> None:
    ensure_indices()
    get_client().index(
        index=INDEX_POSTS,
        id=str(post["post_id"]),
        document={
            "author_id": str(post["author_id"]),
            "caption": post.get("caption", ""),
            "hashtags": [t.lower() for t in post.get("hashtags", [])],
            "created_at": post.get("created_at"),
        },
    )


def remove_post(post_id: str) -> None:
    from elasticsearch import NotFoundError

    ensure_indices()
    try:
        get_client().delete(index=INDEX_POSTS, id=str(post_id))
    except NotFoundError:
        pass  # already gone — deletion is idempotent


# --- Queries (read endpoints) ----------------------------------------------

def _hit_user(hit: dict) -> dict:
    src = hit["_source"]
    return {
        "user_id": hit["_id"],
        "username": src.get("username", ""),
        "bio": src.get("bio", ""),
    }


def _hit_post(hit: dict) -> dict:
    src = hit["_source"]
    return {
        "post_id": hit["_id"],
        "author_id": src.get("author_id"),
        "caption": src.get("caption", ""),
        "hashtags": src.get("hashtags", []),
        "created_at": src.get("created_at"),
    }


def search_users(q: str, limit: int = 20) -> list[dict]:
    ensure_indices()
    res = get_client().search(
        index=INDEX_USERS,
        size=limit,
        query={"match": {"username": {"query": q, "operator": "and"}}},
    )
    return [_hit_user(h) for h in res["hits"]["hits"]]


def search_posts(q: str, limit: int = 20) -> list[dict]:
    ensure_indices()
    # A leading '#' (or any term) hits both the caption and the hashtag prefix.
    terms = q.lstrip("#")
    res = get_client().search(
        index=INDEX_POSTS,
        size=limit,
        query={
            "bool": {
                "should": [
                    {"match": {"caption": {"query": terms}}},
                    {"match": {"hashtags.autocomplete": {"query": terms}}},
                ],
                "minimum_should_match": 1,
            }
        },
        sort=["_score", {"created_at": "desc"}],
    )
    return [_hit_post(h) for h in res["hits"]["hits"]]


def search(q: str, limit: int = 20) -> dict:
    """Combined search over users and posts (the search bar)."""
    if not q:
        return {"users": [], "posts": []}
    return {"users": search_users(q, limit), "posts": search_posts(q, limit)}


def posts_by_hashtag(tag: str, limit: int = 30) -> list[dict]:
    ensure_indices()
    res = get_client().search(
        index=INDEX_POSTS,
        size=limit,
        query={"term": {"hashtags": tag.lstrip("#").lower()}},
        sort=[{"created_at": "desc"}],
    )
    return [_hit_post(h) for h in res["hits"]["hits"]]


def explore(limit: int = 30) -> list[dict]:
    """Explore grid: most recent posts.

    Recency only for now; engagement signals (likes) can enrich the ranking
    later once interaction counters are wired in.
    """
    ensure_indices()
    res = get_client().search(
        index=INDEX_POSTS,
        size=limit,
        query={"match_all": {}},
        sort=[{"created_at": "desc"}],
    )
    return [_hit_post(h) for h in res["hits"]["hits"]]
