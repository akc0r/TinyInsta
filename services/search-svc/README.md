# search-svc

Search & explore (**Elasticsearch**) — CQRS read model. Full spec: [docs/search-svc.md](../../docs/search-svc.md).

| | |
|---|---|
| Store | Elasticsearch (indices `users`, `posts`) |
| Emits | — |
| Consumes | `user.created`, `post.created`, `post.deleted` |

## Endpoints
`GET /search?q=` · `GET /hashtags/{tag}` · `GET /explore`

> **Rebuildable** index: on corruption, replay the topics from the beginning. No direct user writes.

## Processes
- HTTP: `gunicorn config.wsgi`
- Worker: `python manage.py consume` (indexing)
