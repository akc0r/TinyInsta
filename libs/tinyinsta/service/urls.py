from __future__ import annotations

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from tinyinsta.service.health import health

common_urlpatterns = [
    path("health", health),
    # Prometheus scrape target — every HTTP service exposes /metrics.
    path("", include("django_prometheus.urls")),
    # OpenAPI 3 schema + interactive docs, generated from the DRF views so they
    # always track the running service.
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
