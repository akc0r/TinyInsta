# hometimeline-svc ⭐

Per-follower home feed with **fan-out on write** (Redis). The heart of the project.
Full spec: [docs/hometimeline-svc.md](../../docs/hometimeline-svc.md).

| | |
|---|---|
| Store | Redis — `home:{user_id}` (Sorted Set) |
| Emits | — |
| Consumes | `post.created` (fan-out), `user.followed` (back-fill), `user.unfollowed`, `post.deleted` |

## Strategy
- **Fan-out on write (push)** by default: on `post.created`, push the post into each follower's feed.
- **Back-fill** on `user.followed`: copy the followee's recent posts into the new follower's feed.
- **Hybrid** (later): beyond `CELEBRITY_FOLLOWER_THRESHOLD` followers, skip fan-out; merge at read time with the `usertimeline:{celeb}` lists fetched via the usertimeline-svc **API**.

## Endpoints
`GET /home?cursor=&limit=20` — infinite scroll, keyset cursor `(timestamp, post_id)`.

## Processes
- HTTP: `gunicorn config.wsgi` (feed reads)
- Worker: `python manage.py consume` (fan-out)
