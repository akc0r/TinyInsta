# post-svc

Posts & comments — system of record (**MongoDB**). Full spec: [docs/post-svc.md](../../docs/post-svc.md).

| | |
|---|---|
| Store | MongoDB (`posts`) |
| Auth | Keycloak JWT (JWKS) |
| Emits | `post.created`, `post.commented`, `post.deleted` |
| Consumes | `media.processed` |

## Endpoints (Traefik prefix `/api`)
`POST /posts` · `GET\|DELETE /posts/{id}` · `GET\|POST /posts/{id}/comments`

## Processes
- HTTP: `gunicorn config.wsgi` (API)
- Worker: `python manage.py consume` (consumes `media.processed`)

> No SQL ORM: `DATABASES=dummy`, do not run `migrate`. The Mongo repository lives in `posts/mongo.py`.
