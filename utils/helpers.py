"""
utils/helpers.py
================
Shared utility functions used across the framework.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Tuple, Type

from utils.logger import get_logger

logger = get_logger(__name__)


def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    tries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable:
    """
    Decorator to retry a function on specified exceptions.

    Usage::

        @retry(exceptions=(ConnectionError,), tries=3, delay=0.5, backoff=2)
        def flaky_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    logger.warning(
                        "Retry %s after %ss due to: %s", func.__name__, _delay, exc
                    )
                    time.sleep(_delay)
                    _tries  -= 1
                    _delay  *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator


def assert_response_time(elapsed_ms: float, budget_ms: float, label: str = "") -> None:
    """Assert elapsed_ms is within budget. Raises AssertionError with details."""
    tag = f"[{label}] " if label else ""
    assert elapsed_ms <= budget_ms, (
        f"{tag}SLA breach: {elapsed_ms:.1f}ms > budget {budget_ms}ms"
    )


def is_valid_iso8601(value: str) -> bool:
    """Return True if value loosely matches ISO 8601 datetime format."""
    import re
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    return bool(re.match(pattern, value))


def deep_get(d: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts without KeyError."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)  # type: ignore[assignment]
    return d
