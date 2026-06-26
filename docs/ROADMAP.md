# Roadmap

Guiding principle: **each phase produces a demonstrable deliverable.** We only move to the next phase once the current phase's demo runs. Datastores are introduced one at a time. The app is demonstrable end-to-end from **Phase 4 (MVP)**.

---

### Phase 0 — Foundations
Monorepo, minimal `docker-compose` (Postgres + Redis + Keycloak + Redpanda + Traefik), one Django "health" service, Next.js shell.
**Demo:** a Next page calls `/api/health` through Traefik; the Keycloak login screen is up.

### Phase 1 — Auth + Profiles · *Postgres*
Keycloak realm/clients, `user-svc` (profiles in Postgres), OIDC login on the Next side, profile CRUD.
**Demo:** I log in via Keycloak and edit my profile.

### Phase 2 — Posts + Upload · *MongoDB + MinIO*
`post-svc` (Mongo), `media-svc` + upload via presigned MinIO URL, **`usertimeline-svc`** (per-author read model, Redis) for the profile grid.
**Demo:** I upload a photo → it appears on my profile.

### Phase 3 — Social graph · *Neo4j*
follow/unfollow in Neo4j (`user-svc`), "people you may know" suggestions (2nd degree).
**Demo:** I follow someone and receive friends-of-friends suggestions.

### Phase 4 — Home timeline + fan-out · *Redpanda + Redis* ⭐
`hometimeline-svc`, fan-out on write, back-fill on follow (reading user timelines), cursor-based infinite scroll.
**Demo:** I follow → that person posts → it shows up in my home feed, infinite scroll.
> 🏁 **MVP: a working Instagram-like** (auth, profiles, follows, posts, feed). Already a solid portfolio project. If you stop here, it is already a success.

### Phase 5 — Real-time interactions
`interaction-svc` (likes in Postgres + counters in Redis), comments (post-svc), `realtime-svc` (Django Channels), live counters.
**Demo:** I like → the counter increments live on another device; I comment.

### Phase 6 — Stories + camera flow
`stories-svc`, web camera capture, 24h TTL, bar + viewer.
**Demo:** I post a story from my camera; it disappears after 24h.

### Phase 7 — Search & explore · *Elasticsearch*
`search-svc`, a users/captions/hashtags index fed by events, search bar + explore page.
**Demo:** I search for a user / a hashtag; explore page.

### Phase 8 — Asynchronous media pipeline
`media-worker`, thumbnails (Pillow) + 720p transcode (ffmpeg), `media.uploaded` → `media.processed`.
**Demo:** I upload a video → thumbnail + 720p variant generated automatically.

### Phase 9 — Notifications + observability + polish ✅
Notification feed (realtime-svc), correlated JSON logs (`tinyinsta.observability`,
`correlation_id` across HTTP + bus), Prometheus/Grafana + Filebeat/Kibana (compose
profile `observability`), rate limiting (Traefik `ratelimit@file`), seed of 10k
users + 1 "celebrity" (`user-svc … manage.py seed`).
**Demo:** live notification center + dashboards.

### Phase 10 — Scale & ops *(optional)* — *delivered, minus Java/Capacitor*
Hybrid fan-out for celebrities (`hometimeline-svc`: read-time merge above
`CELEBRITY_FOLLOWER_THRESHOLD`), Kubernetes (`infra/k8s`, kustomize), nginx/CDN in
front of MinIO (`infra/nginx`, `S3_CDN_URL`), CI/CD (`.github/workflows/ci.yml`).
Capacitor mobile and the optional Java/Spring service swap are intentionally not done.
**Demo:** deployed on a cluster, *hot-user* handled.

---

## Why this sequencing

- **Datastores one at a time**: never six databases to wire up at once.
- **The hard distributed part (Phase 4) isolated**: you don't learn event-driven fan-out while learning something else new.
- **MVP reached early (Phase 4)**: a presentable project exists well before the end → the anti-burnout safety net.
