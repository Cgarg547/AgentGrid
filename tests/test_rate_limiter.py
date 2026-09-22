import pytest
import fakeredis

from app.services.rate_limiter import (
    RateLimitExceeded,
    RedisRateLimiter,
)


def test_rate_limiter_allows_requests_within_limit():
    redis_client = fakeredis.FakeRedis()

    limiter = RedisRateLimiter(
        redis_client=redis_client,
        limit=3,
        window_seconds=60,
    )

    assert limiter.check("test-client") is True
    assert limiter.check("test-client") is True
    assert limiter.check("test-client") is True


def test_rate_limiter_rejects_request_after_limit():
    redis_client = fakeredis.FakeRedis()

    limiter = RedisRateLimiter(
        redis_client=redis_client,
        limit=2,
        window_seconds=60,
    )

    assert limiter.check("test-client") is True
    assert limiter.check("test-client") is True

    with pytest.raises(RateLimitExceeded):
        limiter.check("test-client")


def test_rate_limiter_separates_keys():
    redis_client = fakeredis.FakeRedis()

    limiter = RedisRateLimiter(
        redis_client=redis_client,
        limit=1,
        window_seconds=60,
    )

    assert limiter.check("client-a") is True
    assert limiter.check("client-b") is True

    with pytest.raises(RateLimitExceeded):
        limiter.check("client-a")


def test_rate_limiter_rejects_invalid_limit():
    redis_client = fakeredis.FakeRedis()

    with pytest.raises(ValueError):
        RedisRateLimiter(
            redis_client=redis_client,
            limit=0,
            window_seconds=60,
        )


def test_rate_limiter_rejects_invalid_window():
    redis_client = fakeredis.FakeRedis()

    with pytest.raises(ValueError):
        RedisRateLimiter(
            redis_client=redis_client,
            limit=10,
            window_seconds=0,
        )