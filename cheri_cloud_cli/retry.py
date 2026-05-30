"""Retry utilities with exponential backoff for transient errors."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from .client import CheriClientError

T = TypeVar("T")

# Default retry configuration
DEFAULT_MAX_RETRIES = 5
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 32.0  # seconds

# HTTP status codes that are safe to retry (transient errors)
RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}

# Error messages that indicate permanent failures (should NOT retry)
PERMANENT_FAILURE_PATTERNS = [
    "auth",
    "authentication",
    "unauthorized",
    "forbidden",
    "workspace denied",
    "permission",
    "provider invalid",
    "invalid provider",
    "not found",
    "file not found",
    "does not exist",
    "invalid credentials",
    "invalid_api_url",
    "connection failed",
]


def _is_retryable_error(exc: Exception) -> bool:
    """Determine if an exception is safe to retry."""
    # Don't retry if it's not a CheriClientError (network level errors may be retryable)
    if isinstance(exc, CheriClientError):
        message = str(exc).lower()
        # Check for permanent failure patterns
        for pattern in PERMANENT_FAILURE_PATTERNS:
            if pattern.lower() in message:
                return False
        return True

    # For other exceptions (requests errors, etc.), check if it's transient
    # Network timeouts, connection resets are typically retryable
    import requests

    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True

    # RequestException is the base for all requests errors
    if isinstance(exc, requests.exceptions.RequestException):
        # Check if response has retryable status code
        if hasattr(exc, "response") and exc.response is not None:
            return exc.response.status_code in RETRYABLE_STATUS_CODES
        # Network-level errors are retryable
        return True

    return False


def _should_retry(exc: Exception, attempt: int, max_retries: int) -> bool:
    """Check if we should retry based on exception and attempt count."""
    if attempt >= max_retries:
        return False
    return _is_retryable_error(exc)


def with_retry(
    func: Callable[..., T],
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    on_retry: Callable[[Exception, int], None] | None = None,
    **kwargs,
) -> T:
    """
    Execute a function with exponential backoff retry.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts (default 5)
        initial_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay cap in seconds (default 32.0)
        on_retry: Optional callback called on each retry (exc, attempt)
        **kwargs: Keyword arguments for the function

    Returns:
        The return value of the function

    Raises:
        The last exception if all retries are exhausted
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc

            if not _should_retry(exc, attempt, max_retries):
                raise

            # Calculate delay with exponential backoff
            delay = min(initial_delay * (2 ** attempt), max_delay)

            # Add small jitter to avoid thundering herd
            import random

            jitter = delay * 0.1 * random.random()
            delay = delay + jitter

            if on_retry:
                on_retry(exc, attempt + 1)

            time.sleep(delay)

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry exhausted without error - this should not happen")


def retry_onTransient_error(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
):
    """
    Decorator for adding retry logic to functions.

    Usage:
        @retry_on_transient_error(max_retries=3)
        def my_function():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: object, **kwargs: object) -> T:
            return with_retry(
                func,
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                **kwargs,  # type: ignore[arg-type]
            )

        return wrapper

    return decorator