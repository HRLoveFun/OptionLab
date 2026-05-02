"""In-memory rate limiter (token bucket) and client-IP helper.

Domain:    Utils — Rate Limiting
Context:
  - Simple per-IP counter adequate for a single-machine personal project.
  - For multi-process production use a proper limiter (Redis or flask-limiter).
Contracts:
  - rate_limit(key, max_calls, window_sec) -> tuple[bool, int]
  - client_ip() -> str
Dependencies UPWARD:
  - flask (request)
Dependencies DOWNWARD:
  - routes/*
"""

from __future__ import annotations

import threading
import time

from flask import request

_rate_buckets: dict[str, list[float]] = {}
_rate_lock = threading.Lock()


def rate_limit(key: str, max_calls: int, window_sec: int) -> tuple[bool, int]:
    """Allow up to ``max_calls`` per ``window_sec`` per key.

    Returns ``(allowed, retry_after_seconds)``. When throttled, retry_after
    is the number of seconds until the oldest call in the window expires.
    """
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.get(key, [])
        # Drop expired entries
        bucket = [t for t in bucket if (now - t) < window_sec]
        if len(bucket) >= max_calls:
            retry = int(window_sec - (now - bucket[0])) + 1
            _rate_buckets[key] = bucket
            return False, max(1, retry)
        bucket.append(now)
        _rate_buckets[key] = bucket
    return True, 0


def client_ip() -> str:
    """Return the client IP from X-Forwarded-For or remote_addr."""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"
