# messaging-svc

> Direct messages (1:1), backed by Cassandra.

| | |
|---|---|
| **Language** | Django / DRF |
| **Store** | **Cassandra** (conversations + messages) |
| **Sync dependencies** | none |
| **Authentication** | Keycloak JWT (JWKS) |

## Responsibilities
- Persist direct messages and the per-user conversation list (inbox).
- Emit `message.sent`; **realtime-svc** (the WebSocket hub) delivers it live to the recipient.

Send is HTTP (client→server), receive is WebSocket (server→client) — the usual chat split.
messaging-svc owns persistence; it does **not** own the socket.

## Cassandra data model (query-first)

```cql
messages_by_conversation (
  conversation_id text, message_id timeuuid, sender_id text, recipient_id text,
  body text, created_at timestamp,
  PRIMARY KEY ((conversation_id), message_id)
) WITH CLUSTERING ORDER BY (message_id DESC)

conversations_by_user (
  user_id text, conversation_id text, peer_id text,
  last_message text, last_message_at timestamp,
  PRIMARY KEY ((user_id), conversation_id)
)
```

- A 1:1 `conversation_id` is deterministic: `":".join(sorted([a, b]))` — stable regardless of sender.
- A conversation's messages are one sequential partition read (clustering by `timeuuid` DESC),
  paginated by the last `message_id`. A user's inbox is one partition read, ordered client-side.

## REST API

| Method | Route | Description |
|---|---|---|
| `GET` | `/messaging/conversations` | The caller's inbox, most-recent first |
| `POST` | `/messaging/conversations/start` | `{peer_id}` → `{conversation_id}` |
| `GET` | `/messaging/conversations/{id}/messages?cursor=` | Messages, newest first |
| `POST` | `/messaging/conversations/{id}/messages` | `{body}` → send (only members) |

## Events

**Emits:** `message.sent`
**Consumes:** —

## Notes
- Why Cassandra: messages are append-only, high-volume, time-ordered, partitioned by
  conversation, and never need cross-row integrity or joins — the canonical wide-column fit.
  Postgres keeps the data that *does* need uniqueness/transactions (likes, profiles, notifications).
- Schema is created idempotently at startup (`manage.py init_cassandra`, `CREATE ... IF NOT EXISTS`).
- Single-node `SimpleStrategy` keyspace in dev; replication factor is env-tunable.
