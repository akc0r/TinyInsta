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

## Local dev
```bash
python manage.py migrate   # creates the `likes` table (interaction_svc DB)
python manage.py runserver 0.0.0.0:8000
```

> The Redis counter (`likes:{post_id}`) is a rebuildable read model: a cold key is
> re-projected from the Postgres `likes` count on the next read/write.
