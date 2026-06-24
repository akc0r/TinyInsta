# search-svc

> Search and the explore page.

| | |
|---|---|
| **Language** | Django / DRF |
| **Store** | **Elasticsearch** |
| **Sync dependencies** | none |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Index users and posts for search.
- Serve full-text search (users, hashtags, captions) and the explore page.

It is a **CQRS read model**: no direct user writes, the index is entirely fed by events.

## Elasticsearch indices

```
users:  { user_id, username, bio }
posts:  { post_id, author_id, caption, hashtags[], created_at }
```

## REST API

| Method | Route | Description |
|---|---|---|
| `GET` | `/search?q=` | Search users + posts |
| `GET` | `/hashtags/{tag}` | Posts for a hashtag |
| `GET` | `/explore` | Popular/recent posts (explore page) |

## Events

**Emits:** —
**Consumes:** `user.created` (index user), `post.created` (index post), `post.deleted` (remove from index)

## Notes
- The index is **rebuildable**: on corruption, rebuild it by replaying events from the start of the topics.
- Autocomplete is possible via Elasticsearch analyzers (edge n-grams) on `username` and `hashtags`.
- The explore ranking can combine recency + engagement signals (enrich later with like counters).
