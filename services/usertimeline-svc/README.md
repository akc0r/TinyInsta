# usertimeline-svc

Per-author read model (the profile grid) on **Redis**. Full spec: [docs/usertimeline-svc.md](../../docs/usertimeline-svc.md).

| | |
|---|---|
| Store | Redis — `usertimeline:{author_id}` (Sorted Set) |
| Emits | — |
| Consumes | `post.created`, `post.deleted` |

This is a **CQRS read model**, fully rebuildable from events — no system of record here.
"Fan-out to self" (1 post = 1 entry), so there is no fan-out explosion.
It also serves as the read building block for the home timeline in hybrid mode.

## Endpoints
`GET /usertimeline/{author_id}?cursor=&limit=20`

## Processes
- HTTP: `gunicorn config.wsgi` (reads)
- Worker: `python manage.py consume` (builds the read model)
