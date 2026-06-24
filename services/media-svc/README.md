# media-svc

Upload reception via **presigned MinIO URLs** + metadata (**lightweight MongoDB**).
Full spec (svc + worker): [docs/media-svc.md](../../docs/media-svc.md).

| | |
|---|---|
| Stores | MinIO (binaries) + MongoDB (`media`) |
| Emits | `media.uploaded` |
| Consumes | — |

## Endpoints
`POST /media/upload-url` (presigned URL) · `POST /media` (register, `pending`) · `GET /media/{id}`

## Flow
The client requests a presigned URL, PUTs the file **directly** to MinIO, then registers the
media here → `media.uploaded` → **media-worker** generates thumbnails/variants → `media.processed`.
See [`../media-worker`](../media-worker).

> No SQL ORM: `DATABASES=dummy`, do not run `migrate`. The Mongo repository lives in `media/mongo.py`.
