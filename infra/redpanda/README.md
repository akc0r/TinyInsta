# Redpanda — event bus (Kafka API)

A single binary, Kafka-compatible API → same clients (`confluent-kafka`).

## Topics
**One topic per event type** (convention: topic name == type, e.g. `post.created`).
Auto-creation is enabled in dev; in production they are declared explicitly (partitions,
replication).

Manually create a topic partitioned by entity (per-key ordering):

```bash
docker compose exec redpanda \
  rpk topic create post.created --partitions 3 --replicas 1
```

## Console
The optional web console (`tools` profile) runs at http://localhost:8085 to inspect topics,
messages, and consumer groups.

## Consumer groups
One group per service (`group.id = <svc>`) → independent offsets, replay, and multiple
instances per service. See `libs/tinyinsta/bus` and [docs/EVENTS.md](../../docs/EVENTS.md).
