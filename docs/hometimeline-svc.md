# hometimeline-svc ⭐

> The **home page** feed: the aggregate of posts from every account a user follows, merged and sorted. The distributed core of the project.

| | |
|---|---|
| **Language** | Django / DRF |
| **Store** | Redis (sorted sets) |
| **Sync dependencies** | user-svc (followers), usertimeline-svc (reads in hybrid mode) |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Maintain each user's home timeline (a read model derived from events).
- Serve that timeline with infinite scroll.

## Fan-out strategy

**Fan-out on write (push)** — the default:
1. On `post.created`, fetch the author's followers (via user-svc, or a local graph cache).
2. Push `post_id` into `home:{follower}` for each one.

```
home:{user_id}  -> Redis Sorted Set (member = post_id, score = timestamp)
```

**Back-fill** — on `user.followed`, inject the followee's N most recent posts (read from **usertimeline-svc**) into the follower's home timeline.

**Hybrid — handling the celebrity problem:**
> For an account with very many followers, we **do not** fan out on write (too expensive). Instead, at read time, a follower's home timeline is computed as:
>
> `home:{follower}` (entries pushed by normal accounts) **⊕** the `usertimeline:{celeb}` lists pulled from **usertimeline-svc** for each large account followed.
>
> This is where `hometimeline-svc` **reads the user timelines**: the per-author read building block becomes the source for celebrities. This is the authentic Twitter architecture for the *hot-user problem*.

## Infinite scroll

Keyset cursor pagination `(timestamp, post_id)`, never `OFFSET`.

| Method | Route | Description |
|---|---|---|
| `GET` | `/home?cursor=&limit=20` | A page of the home timeline → `{ items, next_cursor }` |

## Events

**Emits:** —
**Consumes:** `post.created` (fan-out), `post.deleted` (remove), `user.followed` (back-fill), `user.unfollowed` (purge)

## Notes
- A **rebuildable** read model: if Redis is lost, rebuild it by replaying the events. The system of record is post-svc.
- Stores only ordered ids; post content is hydrated via post-svc.
- Idempotency: dedupe by `event_id` to avoid duplicate fan-out on redelivery.
