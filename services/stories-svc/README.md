# stories-svc

Ephemeral 24h stories — **Postgres** (metadata) + **Redis** (TTL). Full spec: [docs/stories-svc.md](../../docs/stories-svc.md).

| | |
|---|---|
| Stores | Postgres (`stories`, `story_views`) + Redis (`story:active:{author_id}`, `following:{viewer_id}`, `close_friends:{owner_id}`) |
| Emits | `story.created`, `story.viewed` |
| Consumes | `user.followed`, `user.unfollowed`, `user.close_friend_added`, `user.close_friend_removed` |

## Endpoints
`POST /stories` · `GET /stories/feed` · `POST /stories/{id}/view` · `GET /stories/{id}/views`

## Why it consumes `user.*`
The story bar shows the active stories of accounts the viewer **follows**, and a
`close_friends` story only to the author's close friends. The service keeps local
projections — `following:{viewer_id}` and `close_friends:{owner_id}` — built from
`user.followed/unfollowed` and `user.close_friend_added/removed`, never reading
user-svc's database. Both are rebuildable by replaying the `user.*` topics.

## Audience
`POST /stories` accepts `audience` (`public` default, or `close_friends`). The feed
filters `close_friends` stories to the author + their close-friends set.

## Expiration (two mechanisms)
1. Redis TTL on `story:active:{author_id}` → which authors are "live" in the bar,
   self-clearing after the story's lifetime with no computation.
2. `expires_at` filtered at read time (authoritative, survives a Redis flush) + a
   periodic sweeper (`python manage.py sweep`) that purges expired Postgres rows.

## Processes
- HTTP: `gunicorn config.wsgi`
- Worker: `python manage.py consume`  (maintains the following graph)
- Cron:  `python manage.py sweep`     (purge expired stories, run periodically)
