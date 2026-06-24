# post-svc

> Posts and comments.

| | |
|---|---|
| **Language** | Django / DRF |
| **Store** | **MongoDB** |
| **Sync dependencies** | media-svc (media references) |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Create / read / delete a post.
- Caption, hashtags, media references.
- Comments (embedded documents).

## Data model (MongoDB)

```json
posts: {
  "_id": "ObjectId",
  "author_id": "UUID",
  "caption": "string",
  "hashtags": ["string"],
  "media_ids": ["UUID"],
  "comments": [
    { "comment_id": "UUID", "author_id": "UUID", "body": "string", "created_at": "date" }
  ],
  "created_at": "date"
}
```

> Comments stay embedded as long as the volume is reasonable. If a post can accumulate thousands of comments, switch to a separate `comments` collection keyed by `post_id`.

## REST API

| Method | Route | Description |
|---|---|---|
| `POST` | `/posts` | Create a post |
| `GET` | `/posts/{id}` | Read a post |
| `DELETE` | `/posts/{id}` | Delete |
| `POST` | `/posts/{id}/comments` | Comment |
| `GET` | `/posts/{id}/comments` | List comments |

## Events

**Emits:** `post.created`, `post.commented`, `post.deleted`
**Consumes:** `media.processed` (update references to the generated variants)

## Notes
- post-svc is the **system of record** for posts; it does not serve timelines (read models). A profile's post list is served by **usertimeline-svc**.
- `post.created` triggers, with no direct call, the fan-out in **hometimeline-svc** (N entries across followers) **and** **usertimeline-svc** (1 entry for the author), as well as indexing in search-svc.
- Hashtags extracted from the caption are propagated in the event for indexing.
