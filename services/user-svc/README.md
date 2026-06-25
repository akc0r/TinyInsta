# user-svc

User profiles (**Postgres**) and the **social graph** (**Neo4j**). Full spec: [docs/user-svc.md](../../docs/user-svc.md).

| | |
|---|---|
| Stores | Postgres (`profiles`) + Neo4j (graph) |
| Auth | Keycloak JWT (JWKS) |
| Emits | `user.created`, `user.followed/unfollowed`, `user.blocked/unblocked`, `user.close_friend_added/removed` |
| Consumes | — |

## Endpoints (Traefik prefix `/api`)
`GET /users/{id}` · `PATCH /users/me` · `POST\|DELETE /users/{id}/follow` · `POST\|DELETE /users/{id}/block` · `POST\|DELETE /users/{id}/close-friend` · `GET /users/me/close-friends` · `GET /users/{id}/followers` · `GET /users/{id}/following` · `GET /users/me/suggestions`

## Layout
- `users/models.py` — `Profile` (Postgres)
- `users/graph.py` — Neo4j access (follow, block, close-friend, counts, suggestions)
- `users/views.py` — DRF endpoints

Blocking severs `FOLLOWS`/`CLOSE_FRIEND` edges both ways and re-emits the
matching `user.unfollowed` / `user.close_friend_removed` events so the feed read
models converge. See [docs/user-svc.md](../../docs/user-svc.md) for the scope note.

## Local dev
```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```
