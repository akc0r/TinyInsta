# services/

One directory per **bounded context**. All HTTP services share the same structure
(consistent boilerplate); the business logic is left to implement (marked `# TODO`).

| Service | Store(s) | Emits | Consumes |
|---|---|---|---|
| [user-svc](user-svc) | Postgres + Neo4j | user.created/followed/unfollowed, user.blocked/unblocked, user.close_friend_added/removed | — |
| [post-svc](post-svc) | MongoDB | post.created/commented/deleted | media.processed |
| [usertimeline-svc](usertimeline-svc) | Redis | — | post.created/deleted |
| [hometimeline-svc](hometimeline-svc) | Redis | — | post.created, user.followed/unfollowed, post.deleted |
| [interaction-svc](interaction-svc) | Postgres + Redis | post.liked/unliked | — |
| [stories-svc](stories-svc) | Postgres + Redis | story.created/viewed | user.followed/unfollowed, user.close_friend_added/removed |
| [media-svc](media-svc) | MinIO + MongoDB | media.uploaded | — |
| [media-worker](media-worker) | MinIO | media.processed | media.uploaded |
| [search-svc](search-svc) | Elasticsearch | — | user.created, post.created/deleted |
| [realtime-svc](realtime-svc) | Redis + Postgres | — | post.liked/commented, story.created, user.followed |

## Anatomy of an HTTP service

```
<svc>/
├── Dockerfile            # build (context = repo root, bundles libs/)
├── requirements.txt      # service-specific deps (+ gunicorn)
├── manage.py
├── config/               # Django project: settings (extends tinyinsta.service), urls, asgi, wsgi
└── <app>/                # bounded context
    ├── models.py         # (when a relational store is used)
    ├── views.py          # DRF endpoints (skeleton)
    ├── urls.py
    ├── store.py / mongo.py / index.py / ...   # store access
    └── management/commands/consume.py         # bus worker (when the service consumes)
```

## Cross-cutting conventions (provided by `libs/tinyinsta`)
- **Settings**: `from tinyinsta.service.settings import *`, then override (apps, DB).
- **Auth**: `KeycloakJWTAuthentication` enabled by default (all endpoints protected).
- **Health**: `GET /health` via `tinyinsta.service.urls.common_urlpatterns`.
- **Bus**: `tinyinsta.bus.Producer` / `Consumer`, contract in `tinyinsta.events`.
- **Golden rule**: a service never reads another service's database (API or events only).

## Running a single service (dev)
```bash
docker compose --profile infra --profile user-svc up -d --build
# or outside Docker, from the service directory:
pip install -e "../../libs[django]" -r requirements.txt
python manage.py migrate         # relational services only
python manage.py runserver 0.0.0.0:8000
python manage.py consume         # worker (consuming services)
```
