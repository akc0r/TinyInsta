# ranking-svc

> Algorithmic feed ranking (recency ⊕ engagement ⊕ affinity).

| | |
|---|---|
| **Language** | Django / DRF |
| **Store** | **Redis** (engagement + affinity signals) |
| **Sync dependencies** | none (called *by* hometimeline-svc) |
| **Authentication** | internal only — no Traefik route, `AllowAny`, called server-to-server |

## Responsibilities
- Maintain, per post, an **engagement** signal (likes + comments, log-damped) and, per
  `(viewer, author)`, an **affinity** counter — both derived from `post.*` events.
- Score a batch of candidate posts for a viewer and return them ordered.

It is a **CQRS read model**: no direct user writes, all signals come from events and are rebuildable.

## Scoring

```
score = w_recency · 0.5^(age_h / half_life)      # exponential recency decay
      + w_engagement · log1p(engagement)          # damped so virality can't dominate
      + w_affinity · log1p(affinity(viewer,author))
      + (reel ? w_reel : 0)
```

All weights and the half-life are env-tunable (`RANK_W_*`, `RANK_RECENCY_HALF_LIFE_H`).

## REST API

| Method | Route | Description |
|---|---|---|
| `POST` | `/ranking/score` | Body `{viewer_id, items:[post_id]}` → `{scores, ranked}` |

## Events

**Emits:** —
**Consumes:** `post.created` (metadata), `post.deleted` (drop), `post.liked`/`post.unliked`
(engagement + affinity), `post.commented` (engagement + affinity)

## Notes
- hometimeline-svc calls `/ranking/score` at feed-read time and reorders **within the page**;
  keyset pagination stays chronological. If ranking-svc is off (`RANKING_ENABLED=false`) or
  unreachable, the feed degrades cleanly to chronological order.
- Signals carry a 30-day TTL to bound Redis; rebuildable by replaying the `post.*` topics.
