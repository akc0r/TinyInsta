# realtime-svc

**WebSocket** gateway (Django Channels) + notifications. Full spec: [docs/realtime-svc.md](../../docs/realtime-svc.md).

| | |
|---|---|
| Stores | Redis (channel layer / pub-sub) + Postgres (`notifications`) |
| Emits | — |
| Consumes | `post.liked`, `post.commented`, `story.created`, `user.followed` |

## API
`WS /ws` (JWT validated at handshake) · `GET /notifications` · `POST /notifications/{id}/read`

## Processes
- ASGI: `daphne config.asgi:application` (WebSocket — **not** gunicorn)
- Worker: `python manage.py consume` (bridges bus → channel layer)

> The channel layer runs on Redis → multiple instances share connections (horizontal scaling).
> For likes, the event carries `new_count` → push the counter directly without re-reading the DB.
