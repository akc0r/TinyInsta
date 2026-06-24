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
- Social graph: follow / unfollow.
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
```

## REST API

| Method | Route | Description |
|---|---|---|
| `GET` | `/users/{id}` | Public profile |
| `PATCH` | `/users/me` | Update own profile |
| `POST` | `/users/{id}/follow` | Follow |
| `DELETE` | `/users/{id}/follow` | Unfollow |
| `GET` | `/users/{id}/followers` | Followers list |
| `GET` | `/users/{id}/following` | Following list |
| `GET` | `/users/me/suggestions` | Suggestions (friends-of-friends, Neo4j) |

## Events

**Emits:** `user.created`, `user.followed`, `user.unfollowed`
**Consumes:** —

## Notes
- `user_id` is the Keycloak JWT `sub` → no password management here (delegated to Keycloak).
- On first login, a profile is created and `user.created` is emitted (consumed by search-svc for indexing and by realtime-svc).
- The Neo4j graph and the Postgres table are updated within the same application operation; on inconsistency, Postgres is authoritative for user existence, Neo4j for relationships.
