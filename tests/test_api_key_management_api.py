from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.api_keys import router
from app.core.database import SessionLocal
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def create_test_key():
    return api_key_service.create_api_key(
        "api-key-management-test",
        scopes=[
            "api_keys:manage",
        ],
    )


def test_create_api_key():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()

    try:
        response = TestClient(app).post(
            "/api-keys",
            json={"name": "created-key"},
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["key_id"]
        assert data["name"] == "created-key"
        assert data["api_key"]
        assert data["enabled"] is True
        assert data["created_at"]

        created_key_id = data["key_id"]

        api_key_service.delete_api_key(created_key_id)

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )


def test_list_api_keys():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()
    second_key, _ = create_test_key()

    try:
        response = TestClient(app).get(
            "/api-keys",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert "api_keys" in data
        assert "count" in data
        assert data["count"] >= 2

        key_ids = {
            item["key_id"]
            for item in data["api_keys"]
        }

        assert bootstrap_key.key_id in key_ids
        assert second_key.key_id in key_ids

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )
        api_key_service.delete_api_key(
            second_key.key_id
        )


def test_get_api_key():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()

    try:
        response = TestClient(app).get(
            f"/api-keys/{bootstrap_key.key_id}",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["key_id"] == bootstrap_key.key_id
        assert data["name"] == bootstrap_key.name
        assert data["enabled"] is True

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )


def test_disable_and_enable_api_key():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()
    target_key, _ = create_test_key()

    try:
        disable_response = TestClient(app).post(
            f"/api-keys/{target_key.key_id}/disable",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert disable_response.status_code == 200

        disable_data = disable_response.json()

        assert disable_data["key_id"] == target_key.key_id
        assert disable_data["enabled"] is False

        enable_response = TestClient(app).post(
            f"/api-keys/{target_key.key_id}/enable",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert enable_response.status_code == 200

        enable_data = enable_response.json()

        assert enable_data["key_id"] == target_key.key_id
        assert enable_data["enabled"] is True

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )
        api_key_service.delete_api_key(
            target_key.key_id
        )


def test_delete_api_key():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()
    target_key, _ = create_test_key()

    try:
        response = TestClient(app).delete(
            f"/api-keys/{target_key.key_id}",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["deleted"] is True
        assert data["key_id"] == target_key.key_id

        assert (
            api_key_service.get_api_key(
                target_key.key_id
            )
            is None
        )

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )
        api_key_service.delete_api_key(
            target_key.key_id
        )


def test_api_key_management_requires_authentication():
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    response = client.get("/api-keys")

    assert response.status_code == 401

def test_api_key_management_enforces_rate_limit():
    import fakeredis
    import app.security.rate_limit as rate_limit_module

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    bootstrap_key, bootstrap_raw_key = create_test_key()

    fake_redis = fakeredis.FakeRedis()

    original_get_redis_client = rate_limit_module.get_redis_client
    original_rate_limit = rate_limit_module.RATE_LIMIT

    rate_limit_module.get_redis_client = lambda: fake_redis
    rate_limit_module.RATE_LIMIT = 1

    try:
        first_response = client.get(
            "/api-keys",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        second_response = client.get(
            "/api-keys",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )
    finally:
        rate_limit_module.get_redis_client = original_get_redis_client
        rate_limit_module.RATE_LIMIT = original_rate_limit

        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == "Rate limit exceeded."
    assert second_response.headers["Retry-After"] == "60"