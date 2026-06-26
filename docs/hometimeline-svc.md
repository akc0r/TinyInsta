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

**Implementation.** An author becomes a *celebrity* once its follower count (the
local `followers:{id}` cache) reaches `CELEBRITY_FOLLOWER_THRESHOLD` (env,
default 5000); it is then added to the global Redis set `celebrities`. From that
point `post.created` for that author is **not** fanned out (only pushed to the
author's own `home:`). At read time `store.page()` merges, by score:
- the push entries in `home:{follower}`, with
- the recent posts pulled from usertimeline-svc for each celebrity in
  `SINTER following:{follower} celebrities`.

`following:{follower}` is maintained from `user.followed` / `user.unfollowed`,
alongside the existing `followers:{author}`. Deep pagination past a celebrity's
recent window is best-effort.

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
