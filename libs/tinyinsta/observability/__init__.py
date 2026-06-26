"""Cross-cutting observability: correlated structured logging.

A single ``correlation_id`` follows a request across HTTP and the bus, and every
log line is JSON carrying ``service`` + ``correlation_id`` — so one user action
can be traced across services in Kibana.
"""

from tinyinsta.observability.context import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)

__all__ = ["get_correlation_id", "set_correlation_id", "new_correlation_id"]
