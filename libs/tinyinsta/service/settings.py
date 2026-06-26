from __future__ import annotations

import os

from tinyinsta.observability.logging import build_logging

BASE_DIR = os.getcwd()

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

SERVICE_NAME = os.environ.get("SERVICE_NAME", "tinyinsta-svc")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "corsheaders",
    "rest_framework",
    "django_prometheus",
    "tinyinsta.service",
]

# django_prometheus' Before/After middlewares must bookend the stack to time the
# whole request; the correlation id is bound first so every log in between carries it.
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "tinyinsta.service.middleware.CorrelationIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# The browser calls the API through Traefik from the Next.js origin (cross-origin).
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")

ROOT_URLCONF = "config.urls"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "tinyinsta.auth_jwt.KeycloakJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": None,
}

USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# JSON logs stamped with service + correlation_id (see tinyinsta.observability).
LOGGING = build_logging(os.environ.get("LOG_LEVEL", "INFO"))
