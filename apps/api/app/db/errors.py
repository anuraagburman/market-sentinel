"""Retry entire synchronous operations only for transaction concurrency failures."""

from functools import wraps

from sqlalchemy.exc import DBAPIError

RETRYABLE = {"40001", "40P01"}


def retry_transaction(operation):
    @wraps(operation)
    def run(*args, **kwargs):
        for attempt in range(3):
            try:
                return operation(*args, **kwargs)
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) not in RETRYABLE or attempt == 2:
                    raise

    return run
