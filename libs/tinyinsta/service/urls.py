from __future__ import annotations

from django.urls import include, path

from tinyinsta.service.health import health

common_urlpatterns = [
    path("health", health),
    # Prometheus scrape target — every HTTP service exposes /metrics.
    path("", include("django_prometheus.urls")),
]
