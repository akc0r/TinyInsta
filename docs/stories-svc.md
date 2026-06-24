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
story:active:{author_id}  -> 24h TTL key (the "live" story bar)
```

## Expiration
Two combined mechanisms:
1. **Redis TTL**: the `story:active:{author_id}` key expires on its own after 24h → an up-to-date story bar with no computation.
2. **`expires_at` filter + sweeper**: at read time, filter on `expires_at > now()`; a periodic sweep purges expired records from Postgres.

## REST API

| Method | Route | Description |
|---|---|---|
| `POST` | `/stories` | Publish a story |
| `GET` | `/stories/feed` | Active stories of followed accounts |
| `POST` | `/stories/{id}/view` | Record a view |
| `GET` | `/stories/{id}/views` | View list (author) |

## Events

**Emits:** `story.created`, `story.viewed`
**Consumes:** `media.processed`

## Notes
- Media is stored in MinIO via media-svc; stories-svc only handles metadata + TTL.
- `story.created` → realtime-svc pushes the new story into the bar of connected followers.
