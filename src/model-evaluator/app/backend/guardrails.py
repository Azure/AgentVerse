"""Guardrails for a public endpoint backed by a shared managed identity.

Best-effort, in-process (single replica in the demo). Covers: per-IP sliding
rate limit, global concurrency semaphore over model calls, SSE stream cap, and a
refresh debounce so callers can't hammer discovery. None of this replaces real
auth — it just keeps a public demo from becoming an open spending proxy.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from . import config

# Global cap on concurrent in-flight model calls across all requests.
MODEL_SEMAPHORE = asyncio.Semaphore(config.GLOBAL_CONCURRENCY)

_rate: Dict[str, Deque[float]] = defaultdict(deque)
_sse_active = 0
_sse_lock = asyncio.Lock()
_last_refresh = 0.0


def check_rate_limit(client_ip: str) -> bool:
    """Sliding-window per-IP limit. Returns True if the request is allowed."""
    now = time.monotonic()
    window = config.RATE_LIMIT_WINDOW_SECONDS
    q = _rate[client_ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= config.RATE_LIMIT_MAX_REQUESTS:
        return False
    q.append(now)
    return True


def allow_refresh() -> bool:
    """Debounce discovery refresh so ?refresh=1 can't be spammed."""
    global _last_refresh
    now = time.monotonic()
    if now - _last_refresh < config.REFRESH_MIN_INTERVAL_SECONDS:
        return False
    _last_refresh = now
    return True


class SSESlot:
    """Async context manager bounding concurrent SSE streams."""

    def __init__(self) -> None:
        self.acquired = False

    async def __aenter__(self) -> "SSESlot":
        global _sse_active
        async with _sse_lock:
            if _sse_active >= config.MAX_SSE_STREAMS:
                self.acquired = False
                return self
            _sse_active += 1
            self.acquired = True
        return self

    async def __aexit__(self, *exc) -> None:
        global _sse_active
        if self.acquired:
            async with _sse_lock:
                _sse_active = max(0, _sse_active - 1)
