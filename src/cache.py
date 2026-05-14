"""In-memory TTL cache for Garmin API read calls."""
from __future__ import annotations

import functools
import time

_store: dict[tuple, tuple[object, float]] = {}


def cached(ttl_seconds: int = 300):
    """Cache the return value of a function for *ttl_seconds* seconds.

    The cache key is (function qualname, args, sorted kwargs).
    Args must be hashable (strings, ints, None — typical for Garmin tool params).
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__qualname__, args, tuple(sorted(kwargs.items())))
            entry = _store.get(key)
            if entry is not None:
                value, expires_at = entry
                if time.monotonic() < expires_at:
                    return value
            result = fn(*args, **kwargs)
            _store[key] = (result, time.monotonic() + ttl_seconds)
            return result
        return wrapper
    return decorator


def invalidate(prefix: str | None = None) -> None:
    """Remove cache entries whose key starts with *prefix*, or all entries if None."""
    if prefix is None:
        _store.clear()
        return
    for key in [k for k in _store if k[0].startswith(prefix)]:
        del _store[key]
