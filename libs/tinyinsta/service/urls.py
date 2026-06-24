from __future__ import annotations

from django.urls import path

from tinyinsta.service.health import health

common_urlpatterns = [
    path("health", health),
]
