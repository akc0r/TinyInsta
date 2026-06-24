# Build context = repo root (see docker-compose.yml) so libs/ is bundled in.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Shared libraries (event contract, bus client, auth, Django base)
COPY libs /libs
RUN pip install --no-cache-dir -e "/libs[django]"

# Service-specific dependencies
COPY services/user-svc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Service code
COPY services/user-svc/ .

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
