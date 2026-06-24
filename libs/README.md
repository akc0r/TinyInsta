# libs — `tinyinsta` (shared code)

An installable Python package shared by every microservice. It carries **contracts and
plumbing**, not business logic — the goal is to never rewrite the event envelope, JWT
validation, or the consume loop in each service.

```
tinyinsta/
├── events/      # Bus contract: types, envelope, payload schemas
├── bus/         # Redpanda client: producer, consumer, idempotency
├── auth_jwt/    # Keycloak JWT validation via JWKS (DRF auth class)
└── service/     # Shared Django base settings + /health endpoint
```

## Installation

The package is installed in editable mode inside each service's Docker image
(`pip install -e /libs` — see the `Dockerfile`s). Outside Docker:

```bash
pip install -e "libs[django]"   # HTTP services (Django)
pip install -e libs             # media-worker (no Django)
```

## Modules

| Module | Role | Details |
|---|---|---|
| `tinyinsta.events` | Bus contract | Type constants (`POST_CREATED`…), `Envelope`, per-event schemas. Mirrors [docs/EVENTS.md](../docs/EVENTS.md). |
| `tinyinsta.bus` | Redpanda client | `Producer.publish(...)`, `Consumer.run(handler)` with `event_id` deduplication. |
| `tinyinsta.auth_jwt` | Auth | `KeycloakJWTAuthentication` (DRF) validating signatures against the JWKS. |
| `tinyinsta.service` | Django base | `base settings`, `/health` view, logging configuration. |

> ⚠️ Intentionally **skeletal**: the parts left to implement are marked `# TODO`.
