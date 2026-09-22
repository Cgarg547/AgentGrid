from __future__ import annotations

import time

import redis


class RateLimitExceeded(Exception):
    pass


class RedisRateLimiter:
    def __init__(
        self,
        redis_client: redis.Redis,
        limit: int,
        window_seconds: int,
    ):
        if limit <= 0:
            raise ValueError("Rate limit must be greater than zero.")

        if window_seconds <= 0:
            raise ValueError("Rate-limit window must be greater than zero.")

        self.redis_client = redis_client
        self.limit = limit
        self.window_seconds = window_seconds

    def check(self, key: str) -> bool:
        current_window = int(time.time()) // self.window_seconds
        redis_key = f"agentgrid:rate-limit:{key}:{current_window}"

        count = self.redis_client.incr(redis_key)

        if count == 1:
            self.redis_client.expire(
                redis_key,
                self.window_seconds,
            )

        if count > self.limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded for '{key}'."
            )

        return True