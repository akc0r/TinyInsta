# stories-svc

Ephemeral 24h stories — **Postgres** (metadata) + **Redis** (TTL). Full spec: [docs/stories-svc.md](../../docs/stories-svc.md).

| | |
|---|---|
| Stores | Postgres (`stories`, `story_views`) + Redis (`story:active:{author_id}`) |
| Emits | `story.created`, `story.viewed` |
| Consumes | `media.processed` |

## Endpoints
`POST /stories` · `GET /stories/feed` · `POST /stories/{id}/view` · `GET /stories/{id}/views`

## Expiration (two mechanisms)
1. Redis TTL on `story:active:{author_id}` → live story bar with no computation.
2. `expires_at` filtered at read time + a periodic sweeper (purges Postgres).

## Processes
- HTTP: `gunicorn config.wsgi`
- Worker: `python manage.py consume`
