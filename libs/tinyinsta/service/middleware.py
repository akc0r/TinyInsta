"""HTTP edge of the correlation-id chain.

Reads ``X-Correlation-ID`` from the incoming request (the frontend or an
upstream service may set it), or mints one, binds it to the ambient context for
the duration of the request, and echoes it back on the response so the caller —
and the access log — can stitch the trace together.
"""

from __future__ import annotations

from tinyinsta.observability.context import new_correlation_id, set_correlation_id

HEADER = "X-Correlation-ID"
_META_KEY = "HTTP_X_CORRELATION_ID"


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = request.META.get(_META_KEY) or new_correlation_id()
        set_correlation_id(correlation_id)
        response = self.get_response(request)
        response[HEADER] = correlation_id
        return response
