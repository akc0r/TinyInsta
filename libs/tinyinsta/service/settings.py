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
    "drf_spectacular",
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
    # Per-user rate limit; tune via RATELIMIT_USER_RATE / RATELIMIT_ENABLED.
    "DEFAULT_THROTTLE_CLASSES": [
        "tinyinsta.service.throttling.UserRateThrottle",
    ],
    # Drive OpenAPI generation off the DRF views (see SPECTACULAR_SETTINGS).
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# OpenAPI schema (drf-spectacular). Each service serves its own schema at
# /schema, with Swagger UI at /docs and ReDoc at /redoc. SERVICE_NAME is
# env-driven, so the title tracks whichever service loads this base.
SPECTACULAR_SETTINGS = {
    "TITLE": f"TinyInsta — {SERVICE_NAME}",
    "DESCRIPTION": f"REST API for the {SERVICE_NAME} bounded context.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # The docs endpoints stay reachable without a token (the rest of the API is
    # IsAuthenticated by default).
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    # Endpoints are guarded by Keycloak-issued JWTs (Bearer). Declaring the
    # scheme gives Swagger UI an "Authorize" button that sends the token.
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        },
    },
    "SECURITY": [{"jwtAuth": []}],
}

USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# JSON logs stamped with service + correlation_id (see tinyinsta.observability).
LOGGING = build_logging(os.environ.get("LOG_LEVEL", "INFO"))
