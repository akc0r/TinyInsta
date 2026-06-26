# media-worker

Python worker (**no Django**) — asynchronous media processing. Full spec: [docs/media-svc.md](../../docs/media-svc.md).

| | |
|---|---|
| Store | MinIO |
| Emits | `media.processed` |
| Consumes | `media.uploaded` |

## Role
- Images → `thumb` (320px) + `display` (1080px) JPEGs (Pillow).
- Videos → `thumb` poster + `720p` H.264/AAC transcode (ffmpeg).
- Writes variants to MinIO, flips the media doc to `status: ready`, then
  publishes `media.processed` (→ post-svc).

## Run
```bash
python worker.py
```

## Layout
- `worker.py` — consume loop (`tinyinsta.bus.Consumer`): process → store → emit
- `storage.py` — MinIO/S3 read & write (boto3)
- `mongo.py` — shared `media` collection (flip to `ready` + variants)
- `processors/images.py`, `processors/videos.py` — the actual processing
