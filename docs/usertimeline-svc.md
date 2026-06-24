# usertimeline-svc

> The list of **all posts by a given user**, newest first — what you see when opening a profile. A "per-author" read model.

| | |
|---|---|
| **Language** | Django / DRF |
| **Store** | Redis (sorted sets) |
| **Sync dependencies** | none |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Maintain, for each author, the ordered list of their posts.
- Serve a profile's grid/list with infinite scroll.
- **Act as the read building block for hometimeline-svc** in hybrid mode (celebrities).

## Why a separate service (and not a post-svc endpoint)

The "a service never reads another service's database" rule requires it: post-svc owns the posts (Mongo), so usertimeline-svc must keep its **own denormalized copy**, fed by events. Serving a profile = reading **a single** paginated sorted set, without touching Mongo. That is what makes it a true CQRS read model rather than a thin proxy.

```
usertimeline:{author_id}  -> Redis Sorted Set (member = post_id, score = timestamp)
```

This is "fan-out to self": a post creates **one** entry (for its author), no explosion — unlike the home timeline.

## Infinite scroll

Keyset cursor pagination `(timestamp, post_id)`.

| Method | Route | Description |
|---|---|---|
| `GET` | `/usertimeline/{author_id}?cursor=&limit=20` | A user's posts → `{ items, next_cursor }` |

## Events

**Emits:** —
**Consumes:** `post.created` (add for the author), `post.deleted` (remove)

## Notes
- A **rebuildable** read model derived from events; the system of record is post-svc.
- Two distinct consumers of `post.created` coexist: usertimeline-svc (1 entry for the author) and hometimeline-svc (N entries across followers). Each has its own consumer group.
- Idempotency: dedupe by `event_id`.
