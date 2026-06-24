# media-worker

Python worker (**no Django**) — asynchronous media processing. Full spec: [docs/media-svc.md](../../docs/media-svc.md).

| | |
|---|---|
| Store | MinIO |
| Emits | `media.processed` |
| Consumes | `media.uploaded` |

## Role
- Images → thumbnails + resized variants (Pillow).
- Videos → thumbnail + 720p transcode (ffmpeg).
- Writes variants to MinIO, then publishes `media.processed` (→ post-svc, stories-svc).

## Run
```bash
python worker.py
```

## Layout
- `worker.py` — consume loop (`tinyinsta.bus.Consumer`)
- `processors/images.py`, `processors/videos.py` — processing (to implement)
