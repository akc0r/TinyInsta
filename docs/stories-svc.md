# stories-svc

> Ephemeral stories (24h).

| | |
|---|---|
| **Language** | Django / DRF |
| **Stores** | Postgres + Redis (TTL) |
| **Sync dependencies** | media-svc |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Publish a story (media + 24h lifetime).
- Serve the story bar of followed accounts.
- Track views.

## Data model

### Postgres
```
stories(
  id          UUID PK,
  author_id   UUID,
  media_id    UUID,
  audience    TEXT,            -- 'public' | 'close_friends'
  created_at  TIMESTAMPTZ,
  expires_at  TIMESTAMPTZ      -- created_at + 24h
)
story_views(
  story_id    UUID,
  viewer_id   UUID,
  viewed_at   TIMESTAMPTZ,
  PRIMARY KEY (story_id, viewer_id)
)
```

### Redis
```
story:active:{author_id}  -> 24h TTL key (the "live" story bar marker)
following:{viewer_id}     -> SET of accounts the viewer follows (graph projection)
close_friends:{owner_id}  -> SET of an author's close friends (graph projection)
```

The `following:{viewer_id}` and `close_friends:{owner_id}` sets are local
projections of the social graph, built from `user.followed` / `user.unfollowed`
and `user.close_friend_added` / `user.close_friend_removed`. So `/stories/feed`
knows whose stories to show — and who may see a `close_friends` story — without a
sync call to user-svc. Both are rebuildable by replaying `user.*`.

## Audience
A story is `public` (default) or `close_friends`. A `close_friends` story is
returned by `/stories/feed` only to the author themselves and to viewers in the
author's `close_friends:{author_id}` set.

## Expiration
Two combined mechanisms:
1. **Redis TTL**: the `story:active:{author_id}` key expires on its own after 24h → the bar self-clears (which authors are "live") with no computation.
2. **`expires_at` filter + sweeper**: at read time, filter on `expires_at > now()` (authoritative, survives a Redis flush); a periodic sweep (`manage.py sweep`) purges expired records from Postgres.

## REST API

| Method | Route | Description |
|---|---|---|
| `POST` | `/stories` | Publish a story (`media_id`, optional `audience`) |
| `GET` | `/stories/feed` | Active stories of followed accounts |
| `POST` | `/stories/{id}/view` | Record a view |
| `GET` | `/stories/{id}/views` | View list (author) |

## Events

**Emits:** `story.created`, `story.viewed`
**Consumes:** `user.followed`, `user.unfollowed`, `user.close_friend_added`, `user.close_friend_removed`

## Notes
- Media is stored in MinIO via media-svc; stories-svc only handles metadata + TTL. The frontend captures from the web camera (`getUserMedia`), uploads the frame through media-svc's presigned URL, then `POST /stories` with the resulting `media_id`.
- `story.created` → realtime-svc pushes the new story into the bar of connected followers.
