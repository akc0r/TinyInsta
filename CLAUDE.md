# CLAUDE.md — TinyInsta (root)

Instagram-like clone built as a **real distributed system**: event-driven Django
microservices + polyglot persistence, orchestrated with Docker Compose. The goal is to
demonstrate architecture & patterns (CQRS, fan-out, polyglot stores), **not** scale.

> Read first: `README.md` (full pitch + roadmap) and `docs/` (authoritative specs).
> This file is the fast-orientation map; the `docs/*.md` are the source of truth.

## Repository layout

```
tinyinsta/
├── frontend/      # Next.js 16 / React 19 PWA              → see frontend/CLAUDE.md
├── services/      # one Django service per bounded context → see services/CLAUDE.md
├── libs/          # shared Python pkg `tinyinsta` (auth, bus, events, Django base)
├── infra/         # postgres init, traefik, keycloak realm, redpanda config
├── docs/          # 📚 ARCHITECTURE, DATA-STORES, EVENTS, FRONTEND, per-service specs
├── docker-compose.yml   # everything, gated by profiles
├── Makefile       # shortcuts (make help)
└── .env(.example) # all config (ports, creds, hosts)
```

## Architecture in one breath

- **Frontend** (Next.js) → **Traefik** gateway (`http://localhost/api`) → **services** (Django/DRF).
- **Keycloak** issues OIDC/JWT; each service validates the JWT itself (JWKS) — no session.
- Services talk to each other **only through the bus** (Redpanda, Kafka API) — never by reading
  another service's database. Sync calls are avoided; events are the integration contract.
- **CQRS**: feed (Redis) and search index (Elasticsearch) are rebuildable *read models*
  derived from events. System of record ≠ read views.
- **Polyglot persistence**: Postgres (integrity), MongoDB (post docs), Neo4j (social graph),
  Elasticsearch (search), Redis (feed/real-time), MinIO (blobs). See `docs/DATA-STORES.md`.

## Services & stores (summary — full table in `services/README.md`)

| Service | Store(s) | Role |
|---|---|---|
| user-svc | Postgres + Neo4j | profiles + social graph (follow, suggestions) |
| post-svc | MongoDB | posts + comments |
| usertimeline-svc | Redis | an author's posts (profile feed) |
| hometimeline-svc | Redis | home feed + fan-out-on-write |
| interaction-svc | Postgres + Redis | likes + counters |
| stories-svc | Postgres + Redis | ephemeral 24h stories |
| media-svc (+ media-worker) | MinIO + MongoDB | uploads (presigned) + transcode |
| search-svc | Elasticsearch | user/hashtag search + explore |
| realtime-svc | Redis + Postgres | WebSocket push + notifications |

## Workflow (Makefile — `make help`)

```bash
cp .env.example .env
make infra      # traefik, postgres, redis, redpanda, keycloak
make up         # infra + all datastores + all app services (via profiles)
make ps         # status
make logs SVC=user-svc
make front      # cd frontend && pnpm install && pnpm dev
make down       # stop   |   make clean = down + remove volumes (destroys data)
```

Datastores come online **incrementally** via compose **profiles**
(`infra`, `mongo`, `minio`, `neo4j`, `search`, `apps`) — you don't light up all six on day one.
Ports & URLs: frontend `:3000`, API `localhost/api`, Keycloak `:8080`, MinIO console `:9001`,
Traefik dashboard `:8090`.

## Conventions that matter everywhere

- **Golden rule**: a service never reads another service's DB — API or events only.
- Shared cross-cutting code lives in `libs/tinyinsta` (settings base, JWT auth, bus, event
  schemas). Services extend it, they don't reinvent it.
- Bus event envelope: `{ event_id, type, occurred_at, version, correlation_id, data }`; topic name
  == event type (e.g. `post.created`). Catalog in `docs/EVENTS.md` / `libs/tinyinsta/events/`.
- The system is feature-complete; the architectural core is the home-timeline fan-out
  (hometimeline-svc), including the hybrid read-time path for celebrity accounts.

## Where to look

- How a flow works end-to-end → `docs/ARCHITECTURE.md`
- Why a given database → `docs/DATA-STORES.md`
- Event contract / who emits & consumes what → `docs/EVENTS.md` + `services/README.md` table
- A specific service's spec → `docs/<svc>.md` and `services/<svc>/README.md`
