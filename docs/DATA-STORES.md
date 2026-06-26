# Data stores — polyglot persistence

TinyInsta uses **five databases + one object store**, each chosen for what it does best. This is not gratuitous complexity: it is the *right tool for each problem* principle, and it is the core of the project's technical interest.

## Overview

| Store | Role | Why it is THE right choice |
|---|---|---|
| **Neo4j** | Social graph (follows, recommendations) | The friend graph is the canonical native-graph example. "Friends of friends", suggestions, paths → trivial traversals in Cypher, a nightmare in recursive SQL. |
| **MongoDB** | Posts + comments, media metadata | Flexible-schema documents, embedded comments, reading a post = a single document. |
| **Elasticsearch** | Search & explore | Full-text, hashtag/user search, relevance scoring. A read model fed by events. |
| **Postgres** | Likes, profiles, stories, notifications | Relational integrity, uniqueness constraints (one like per user/post), transactions. Also Keycloak's database. |
| **Redis** | Feed cache, counters, story TTL, pub/sub, sessions | In-memory structures (sorted sets for the feed), native TTL, real-time pub/sub. |
| **MinIO** | Photos, videos, variants | S3-compatible object storage; direct client upload via presigned URL. |

## Who owns what

| Service | Store(s) |
|---|---|
| user-svc | Postgres (profiles) + **Neo4j** (graph) |
| post-svc | **MongoDB** (posts, comments) |
| usertimeline-svc | Redis (per-author sorted set) |
| hometimeline-svc | Redis (per-follower sorted set) |
| interaction-svc | Postgres (likes) + Redis (counters) |
| stories-svc | Postgres + Redis (TTL) |
| media-svc / worker | MinIO (binaries) + MongoDB (metadata) |
| search-svc | **Elasticsearch** |
| realtime-svc | Redis (pub/sub) + Postgres (notifications) |

## Per-store details

### Neo4j — the social graph
- Nodes `(:User {user_id})`, relationships `(:User)-[:FOLLOWS]->(:User)`.
- "People you may know" suggestions = 2nd-degree, not-yet-followed:
  ```cypher
  MATCH (me:User {user_id:$id})-[:FOLLOWS]->()-[:FOLLOWS]->(suggested)
  WHERE NOT (me)-[:FOLLOWS]->(suggested) AND suggested.user_id <> $id
  RETURN suggested.user_id, count(*) AS mutuals
  ORDER BY mutuals DESC LIMIT 10
  ```
- This is where the graph crushes the relational model: the same query in SQL would require expensive recursive self-joins.

### MongoDB — posts & comments
- `posts` document: `{ _id, author_id, caption, hashtags[], media_ids[], comments[], created_at }`.
- Comments stay embedded as long as the volume is reasonable; a linked collection once a post can accumulate thousands of comments.
- Reading a post + its comments = a single document, no JOIN.
- Also used by media-svc for lightweight, schema-flexible media metadata.

### Elasticsearch — search & explore
- Indices: `users` (username, bio), `posts` (caption, hashtags, author_id, created_at).
- Fed by consuming `user.created`, `post.created`, `post.deleted` (CQRS read model).
- Powers full-text search, autocomplete, and the explore page ranking.

### Postgres — relational integrity
- `likes(post_id, user_id, created_at, PK(post_id,user_id))`: the composite primary key **prevents double-likes** at the database level.
- `profiles`, `stories`, `story_views`, `notifications`.
- Keycloak also persists to Postgres (separate database).

### Redis — memory & real-time
- `usertimeline:{author_id}`: Sorted Set (score = timestamp) → all posts by an author (profile), cursor-paginated.
- `home:{user_id}`: Sorted Set (score = timestamp) → a follower's home timeline (fan-out), cursor-paginated.
- `likes:{post_id}`: `INCR` counter, periodically flushed to Postgres (eventual consistency).
- TTL keys for the story bar (native 24h expiry).
- Pub/sub as the Django Channels channel layer (WebSocket).

## Incremental startup

The six stores need not all run at once. Each is gated by a Docker Compose profile, so an environment can bring up only the stores it needs — `make infra` for the baseline, additional profiles (`mongo`, `minio`, `neo4j`, `search`) on top.
