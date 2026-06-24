# interaction-svc

Likes (**Postgres**, uniqueness via composite PK) + counters (**Redis**). Full spec: [docs/interaction-svc.md](../../docs/interaction-svc.md).

| | |
|---|---|
| Stores | Postgres (`likes`) + Redis (`likes:{post_id}`) |
| Emits | `post.liked`, `post.unliked` (with `new_count`) |
| Consumes | — |

## Endpoints
`POST\|DELETE /interactions/posts/{id}/like` · `GET /interactions/posts/{id}/likes`

> The composite PK `(post_id, user_id)` prevents double-likes at the database level.
> `post.liked` / `post.unliked` are consumed by **realtime-svc** for the live counter.
