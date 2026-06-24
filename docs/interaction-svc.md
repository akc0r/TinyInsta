# interaction-svc

> Likes and counters.

| | |
|---|---|
| **Language** | Django / DRF |
| **Stores** | Postgres (likes) + Redis (counters) |
| **Sync dependencies** | none |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Like / unlike a post.
- Maintain the like counter (high write frequency).

## Data model

### Postgres
```
likes(
  post_id     UUID,
  user_id     UUID,
  created_at  TIMESTAMPTZ,
  PRIMARY KEY (post_id, user_id)   -- prevents double-likes at the database level
)
```

### Redis
```
likes:{post_id}   -> integer (INCR / DECR), periodically flushed to Postgres
```

## REST API

| Method | Route | Description |
|---|---|---|
| `POST` | `/interactions/posts/{id}/like` | Like |
| `DELETE` | `/interactions/posts/{id}/like` | Unlike |
| `GET` | `/interactions/posts/{id}/likes` | Counter (read from Redis) |

## Events

**Emits:** `post.liked` (with `new_count`), `post.unliked`
**Consumes:** —

## Notes
- **Eventual consistency by design**: the authoritative counter is in Redis (fast), periodically persisted to Postgres. Postgres holds the truth about *who* liked (the relation), Redis about *how many*.
- `post.liked` carries `new_count` → realtime-svc can push the updated counter to clients without re-reading the database.
- The `(post_id, user_id)` uniqueness in Postgres guards against duplicate requests / retries.
