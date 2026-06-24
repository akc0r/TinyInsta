from __future__ import annotations

import os

from django.http import JsonResponse


def health(_request):
    return JsonResponse(
        {
            "status": "ok",
            "service": os.environ.get("SERVICE_NAME", "tinyinsta-svc"),
        }
    )
