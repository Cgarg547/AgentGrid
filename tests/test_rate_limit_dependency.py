import fakeredis

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.models.api_key import APIKey
from app.security.api_key_auth import require_api_key
from app.security.rate_limit import require_rate_limit


app = FastAPI()


def fake_api_key() -> APIKey:
    return APIKey(
        key_id="test-key",
        key_hash="test-hash",
        name="test",
        scopes="",
        enabled=True,
        created_at=None,
    )


app.dependency_overrides[require_api_key] = fake_api_key


@app.get("/rate-limit-test")
def rate_limit_test(
    _api_key: APIKey = Depends(require_rate_limit),
):
    return {"status": "ok"}


client = TestClient(app)


def test_rate_limit_dependency_allows_request():
    fake_redis = fakeredis.FakeRedis()

    import app.security.rate_limit as rate_limit_module

    original_get_redis_client = rate_limit_module.get_redis_client
    rate_limit_module.get_redis_client = lambda: fake_redis

    try:
        response = client.get("/rate-limit-test")
    finally:
        rate_limit_module.get_redis_client = original_get_redis_client

    assert response.status_code == 200


def test_rate_limit_dependency_rejects_after_limit():
    fake_redis = fakeredis.FakeRedis()

    import app.security.rate_limit as rate_limit_module

    original_get_redis_client = rate_limit_module.get_redis_client
    original_rate_limit = rate_limit_module.RATE_LIMIT

    rate_limit_module.get_redis_client = lambda: fake_redis
    rate_limit_module.RATE_LIMIT = 1

    try:
        first_response = client.get("/rate-limit-test")
        second_response = client.get("/rate-limit-test")
    finally:
        rate_limit_module.get_redis_client = original_get_redis_client
        rate_limit_module.RATE_LIMIT = original_rate_limit

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == "Rate limit exceeded."
    assert second_response.headers["Retry-After"] == "60"