# In-memory, per-process token-bucket rate limiting. Resets on restart and
# is not shared across processes - acceptable for a single API instance,
# would need a shared store (e.g. Redis) once horizontally scaled (Phase 10).

import time

from fastapi import Depends, HTTPException, Request, status

from app.auth import get_current_user_id


class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens added per second
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimiter:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: dict[str, TokenBucket] = {}

    def check(self, key: str) -> bool:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(self.capacity, self.refill_rate)
            self._buckets[key] = bucket
        return bucket.allow()


def _raise_rate_limited() -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests, slow down.",
    )


def limit_by_user(limiter: RateLimiter):
    def dependency(user_id: int = Depends(get_current_user_id)) -> None:
        if not limiter.check(f"user:{user_id}"):
            _raise_rate_limited()

    return dependency


def limit_by_ip(limiter: RateLimiter):
    def dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        if not limiter.check(f"ip:{client_host}"):
            _raise_rate_limited()

    return dependency


# capacity = burst size, refill_rate = steady-state tokens/sec.
# /agent is LLM-backed (DB + retrieval + Groq call) - tightest limit.
# /watchlist is DB-only - moderate.
# /products/search is unauthenticated and a single indexed query - loosest.
agent_limiter = RateLimiter(capacity=5, refill_rate=5 / 60)
watchlist_limiter = RateLimiter(capacity=20, refill_rate=20 / 60)
search_limiter = RateLimiter(capacity=60, refill_rate=1)
