from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.redis import get_redis_client
from app.models.api_key import APIKey
from app.security.api_key_auth import require_api_key
from app.services.rate_limiter import RateLimitExceeded, RedisRateLimiter


RATE_LIMIT = 60
RATE_LIMIT_WINDOW_SECONDS = 60


def require_rate_limit(
    api_key: APIKey = Depends(require_api_key),
):
    limiter = RedisRateLimiter(
        redis_client=get_redis_client(),
        limit=RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )

    try:
        limiter.check(api_key.key_id)
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )

    return api_key