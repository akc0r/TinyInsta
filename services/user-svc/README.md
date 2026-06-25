# user-svc

User profiles (**Postgres**) and the **social graph** (**Neo4j**). Full spec: [docs/user-svc.md](../../docs/user-svc.md).

| | |
|---|---|
| Stores | Postgres (`profiles`) + Neo4j (graph) |
| Auth | Keycloak JWT (JWKS) |
| Emits | `user.created`, `user.followed`, `user.unfollowed` |
| Consumes | — |

## Endpoints (Traefik prefix `/api`)
`GET /users/{id}` · `PATCH /users/me` · `POST\|DELETE /users/{id}/follow` · `GET /users/{id}/followers` · `GET /users/{id}/following` · `GET /users/me/suggestions`

## Layout
- `users/models.py` — `Profile` (Postgres)
- `users/graph.py` — Neo4j access (follow / unfollow / counts / suggestions)
- `users/views.py` — DRF endpoints

## Local dev
```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```
