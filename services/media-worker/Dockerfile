# Build context = repo root (see docker-compose.yml) so libs/ is bundled in.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ffmpeg for video transcoding (system package).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# tinyinsta-libs WITHOUT the [django] extra: the worker does not need Django.
COPY libs /libs
RUN pip install --no-cache-dir -e /libs

COPY services/media-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/media-worker/ .

CMD ["python", "worker.py"]
