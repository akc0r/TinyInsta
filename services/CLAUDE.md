# CLAUDE.md — services/

One directory per **bounded context**. All HTTP services share the **same Django/DRF
boilerplate** (provided by `libs/tinyinsta`); only the bounded-context logic differs.
See `services/README.md` for the per-service emits/consumes table and `docs/<svc>.md` for specs.

## Golden rules

- **A service never reads another service's database.** Integration is via the bus (events)
  or, rarely, a public HTTP endpoint — never shared tables.
- **Read models are rebuildable.** Redis feeds and the ES index are derived from events; they
  are not the system of record. Treat them as caches that can be re-projected.
- Don't duplicate cross-cutting code into a service — extend `libs/tinyinsta` instead.

## Anatomy of an HTTP service

```
<svc>/
├── Dockerfile            # build context = REPO ROOT (so it can bundle libs/)
├── requirements.txt      # service-specific deps + gunicorn (libs installed separately)
├── manage.py
├── config/               # Django project: settings/urls/asgi/wsgi
│   └── settings.py       # `from tinyinsta.service.settings import *` then override
└── <app>/                # the bounded context
    ├── models.py         # only when a relational store (Postgres) is used
    ├── views.py          # DRF endpoints
    ├── urls.py
    ├── store.py / mongo.py / graph.py / index.py   # store access layer
    └── management/commands/consume.py              # bus worker (consuming services)
```

## What `libs/tinyinsta` gives every service

- **Settings base** — `from tinyinsta.service.settings import *`, then set `SERVICE_NAME`,
  append to `INSTALLED_APPS`, and declare `DATABASES` / store config. Example: see
  `user-svc/config/settings.py`.
- **Auth** — `KeycloakJWTAuthentication` is the default DRF auth class and `IsAuthenticated`
  the default permission → **every endpoint is protected unless explicitly opened**. JWTs are
  validated against Keycloak's JWKS (`libs/tinyinsta/auth_jwt/`). No Django sessions/users.
- **Health** — `GET /health` via `tinyinsta.service.urls.common_urlpatterns`.
- **OpenAPI docs** — drf-spectacular, also via `common_urlpatterns`: `GET /schema` (OpenAPI 3),
  `GET /docs` (Swagger UI), `GET /redoc`. Auto-generated from the DRF views and reachable
  without a token; the Bearer/JWT scheme is declared so Swagger UI's "Authorize" works. Hand-written
  `APIView`s have no serializer, so bodies are generic — add `@extend_schema` to enrich a view.
- **Bus** — `tinyinsta.bus.Producer` / `Consumer` over Redpanda (confluent-kafka).
  Idempotent producer; consumers should be idempotent too (`bus/idempotency.py`).
- **CORS** — preconfigured for the Next.js origin (browser hits the API cross-origin via Traefik).

## Bus / event contract

- Envelope: `{ event_id, type, occurred_at, version, data }` (`events/envelope.py`).
- **Topic name == event type**, e.g. `post.created`, `user.followed` (constants in
  `events/types.py`, payload schemas in `events/schemas.py`).
- Publish: `Producer().publish(POST_CREATED, data, key=author_id)`.
  Consume: a `consume.py` management command runs a `Consumer` loop.
- Full catalog & who-emits/consumes-what: `docs/EVENTS.md` + `services/README.md`.

## Running a single service (dev)

```bash
# Via compose (preferred), per-service profile:
docker compose --profile infra --profile user-svc up -d --build

# Or bare, from the service directory:
pip install -e "../../libs[django]" -r requirements.txt
python manage.py migrate              # relational services only
python manage.py runserver 0.0.0.0:8000
python manage.py consume              # bus worker, consuming services only
```

## Adding / modifying a service

1. Check `docs/<svc>.md` for the intended spec before changing behavior.
2. Keep config minimal: extend the settings base, don't copy it.
3. New event? Add the type/schema in `libs/tinyinsta/events/` and document it in `docs/EVENTS.md`
   so producers and consumers stay in sync.
4. Relational schema change → Django migration. Redis/ES projections → make sure they can be
   rebuilt from events (no irreplaceable state).
