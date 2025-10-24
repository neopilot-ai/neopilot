from typing import Dict, Optional

import structlog

__all__ = [
    "log_exception",
]

log = structlog.stdlib.get_logger("exceptions")


def log_exception(ex: BaseException, extra: Optional[Dict] = None) -> None:
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
        additional_details=extra,
        exc_info=ex,
    )
