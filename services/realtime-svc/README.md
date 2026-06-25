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

## Channels & groups
- WS handshake auth: the JWT is passed as `?token=...` (browsers can't set headers on a
  WebSocket); `realtime/middleware.py` validates it against Keycloak's JWKS.
- A socket joins `user.{id}` (its notification stream) and may `{"action":"subscribe","post_id":…}`
  to `post.{id}` groups for the posts on screen (live like/comment counters).
- Notification recipients: `follow` → the followee; `comment` → the post owner (carried on the
  event as `post_author_id`). Likes are **live-counter only** — the post owner isn't on the event.

## Local dev
```bash
python manage.py migrate                # creates the `notifications` table
daphne -b 0.0.0.0 -p 8000 config.asgi:application   # WS + REST (ASGI)
python manage.py consume                # worker: bus → channel layer + persist
```
