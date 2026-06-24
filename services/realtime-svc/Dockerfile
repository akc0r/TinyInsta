# Build context = repo root (see docker-compose.yml) so libs/ is bundled in.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY libs /libs
RUN pip install --no-cache-dir -e "/libs[django]"

COPY services/realtime-svc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/realtime-svc/ .

EXPOSE 8000
# ASGI (WebSocket) -> daphne, not gunicorn/wsgi.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
