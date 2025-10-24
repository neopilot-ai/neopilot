import traceback
from typing import Any, Dict, Optional

import structlog
from asgi_correlation_id.context import correlation_id

__all__ = [
    "log_exception",
]

log = structlog.stdlib.get_logger("exceptions")


def log_exception(ex: Exception, extra: Optional[Dict] = None, **kwargs: Any) -> None:
    """Log the exception with the correlation ID.

    Args:
    ex (``Exception``):
        Raised exception during application runtime.
    extra (``dict``, `optional`):
        Additional metadata for the exception.
    """
    status_code = getattr(ex, "code", None)
    exception_class = type(ex).__name__

    if extra is None:
        extra = {}

    log.error(
        str(ex),
        status_code=status_code,
        exception_class=exception_class,
        backtrace=traceback.format_exc(),
        correlation_id=correlation_id.get(),
        extra=extra,
        **kwargs,
    )
