# user-svc

> User profiles and the **social graph** (follows, recommendations).

| | |
|---|---|
| **Language** | Django / DRF |
| **Stores** | Postgres (profiles) + **Neo4j** (graph) |
| **Sync dependencies** | none |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Profile CRUD (username, bio, avatar).
- Social graph: follow / unfollow, **block / unblock**, **close friends**.
- "People you may know" recommendations (2nd-degree in the graph).

## Data model

### Postgres
```
profiles(
  user_id     UUID PK,      -- = the Keycloak token's `sub`
  username    TEXT UNIQUE,
  bio         TEXT,
  avatar_url  TEXT,
  created_at  TIMESTAMPTZ
)
```

### Neo4j
```
(:User {user_id})
(:User)-[:FOLLOWS {since}]->(:User)
(:User)-[:BLOCKS {since}]->(:User)         -- one-way; severs FOLLOWS/CLOSE_FRIEND both ways
(:User)-[:CLOSE_FRIEND {since}]->(:User)   -- owner's private close-friends subset
```

## REST API

| Method | Route | Description |
|---|---|---|
| `GET` | `/users/{id}` | Public profile |
| `PATCH` | `/users/me` | Update own profile |
| `POST` | `/users/{id}/follow` | Follow (403 if a block exists either way) |
| `DELETE` | `/users/{id}/follow` | Unfollow |
| `POST` | `/users/{id}/block` | Block (severs follows + close-friend edges both ways) |
| `DELETE` | `/users/{id}/block` | Unblock |
| `POST` | `/users/{id}/close-friend` | Add to close friends |
| `DELETE` | `/users/{id}/close-friend` | Remove from close friends |
| `GET` | `/users/me/close-friends` | My close-friends list |
| `GET` | `/users/{id}/followers` | Followers list |
| `GET` | `/users/{id}/following` | Following list |
| `GET` | `/users/me/suggestions` | Suggestions (friends-of-friends, Neo4j) |

The profile detail payload carries viewer-relative flags `is_following`,
`is_blocking`, `is_close_friend`. A profile whose owner **blocks the viewer**
returns `404` (invisible, same as not existing).

## Events

**Emits:** `user.created`, `user.followed`, `user.unfollowed`, `user.blocked`, `user.unblocked`, `user.close_friend_added`, `user.close_friend_removed`
**Consumes:** —

### Block ripple
Blocking is graph-local but its side effects (a blocked user disappearing from
feeds) are propagated by re-using existing events: `block` deletes the
`FOLLOWS`/`CLOSE_FRIEND` edges and emits the matching `user.unfollowed` /
`user.close_friend_removed` so hometimeline-svc and stories-svc converge without
reading user-svc's database. Enforcing block visibility on every read path
(posts, timelines) is intentionally **out of scope** — block is modelled at the
graph + feed layer, not as a cross-service read filter.

## Notes
- `user_id` is the Keycloak JWT `sub` → no password management here (delegated to Keycloak).
- On first login, a profile is created and `user.created` is emitted (consumed by search-svc for indexing and by realtime-svc).
- The Neo4j graph and the Postgres table are updated within the same application operation; on inconsistency, Postgres is authoritative for user existence, Neo4j for relationships.
