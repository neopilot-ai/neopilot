"""Rate limiting middleware for API endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Optional

import redis.asyncio as redis
from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


class InMemoryRateLimiter:
    """In-memory rate limiter using sliding window algorithm."""

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """Check if request is allowed.

        Args:
            key: Unique identifier for the client (e.g., user_id, IP)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - self.window_size

        # Remove old requests outside the window
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]

        # Check if limit exceeded
        if len(self.requests[key]) >= self.requests_per_minute:
            oldest_request = self.requests[key][0]
            retry_after = int(oldest_request + self.window_size - now) + 1
            return False, retry_after

        # Add current request
        self.requests[key].append(now)
        return True, 0

    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - self.window_size

        current_requests = [req_time for req_time in self.requests[key] if req_time > window_start]

        return max(0, self.requests_per_minute - len(current_requests))


class RedisRateLimiter:
    """Redis-based rate limiter for distributed systems."""

    def __init__(self, redis_client: redis.Redis, requests_per_minute: int = 100, window_size: int = 60):
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size

    async def is_allowed(self, key: str) -> tuple[bool, int]:
        """Check if request is allowed using Redis.

        Args:
            key: Unique identifier for the client

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - self.window_size
        redis_key = f"rate_limit:{key}"

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old requests
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count requests in current window
        pipe.zcard(redis_key)

        # Add current request
        pipe.zadd(redis_key, {str(now): now})

        # Set expiration
        pipe.expire(redis_key, self.window_size)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= self.requests_per_minute:
            # Get oldest request to calculate retry_after
            oldest = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                retry_after = int(oldest_time + self.window_size - now) + 1
                return False, retry_after
            return False, self.window_size

        return True, 0

    async def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - self.window_size
        redis_key = f"rate_limit:{key}"

        # Count requests in current window
        count = await self.redis.zcount(redis_key, window_start, now)
        return max(0, self.requests_per_minute - count)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on API requests."""

    def __init__(
        self,
        app: ASGIApp,
        limiter: InMemoryRateLimiter | RedisRateLimiter,
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        super().__init__(app)
        self.limiter = limiter
        self.key_func = key_func or self._default_key_func

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Default function to extract rate limit key from request.

        Uses user_id if authenticated, otherwise falls back to IP address.
        """
        # Try to get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return f"user:{user.id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # Get rate limit key
        key = self.key_func(request)

        # Check rate limit
        if isinstance(self.limiter, RedisRateLimiter):
            is_allowed, retry_after = await self.limiter.is_allowed(key)
            remaining = await self.limiter.get_remaining(key)
        else:
            is_allowed, retry_after = self.limiter.is_allowed(key)
            remaining = self.limiter.get_remaining(key)

        # Add rate limit headers
        response = None
        if not is_allowed:
            raise RateLimitExceeded(retry_after)

        response = await call_next(request)

        # Add rate limit info to response headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.limiter.window_size)

        return response


def create_rate_limiter(
    redis_url: Optional[str] = None, requests_per_minute: int = 100
) -> InMemoryRateLimiter | RedisRateLimiter:
    """Factory function to create appropriate rate limiter.

    Args:
        redis_url: Redis connection URL. If None, uses in-memory limiter.
        requests_per_minute: Maximum requests allowed per minute.

    Returns:
        Rate limiter instance
    """
    if redis_url:
        redis_client = redis.from_url(redis_url, decode_responses=False)
        return RedisRateLimiter(redis_client, requests_per_minute)
    else:
        return InMemoryRateLimiter(requests_per_minute)
