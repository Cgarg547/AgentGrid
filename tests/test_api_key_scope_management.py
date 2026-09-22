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
        "scope-management-test",
        scopes=[
            "api_keys:manage",
        ],
    )


def test_create_api_key_returns_default_scopes():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()

    try:
        response = TestClient(app).post(
            "/api-keys",
            json={
                "name": "default-scope-key",
            },
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["scopes"] == [
            "executions:control",
            "executions:read",
            "workers:read",
            "workflows:execute",
            "workflows:read",
        ]

        created_key_id = data["key_id"]

        api_key_service.delete_api_key(
            created_key_id
        )

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )


def test_create_api_key_accepts_custom_scopes():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()

    try:
        response = TestClient(app).post(
            "/api-keys",
            json={
                "name": "custom-scope-key",
                "scopes": [
                    "workflows:read",
                    "workflows:execute",
                ],
            },
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["scopes"] == [
            "workflows:execute",
            "workflows:read",
        ]

        created_key_id = data["key_id"]

        api_key_service.delete_api_key(
            created_key_id
        )

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )


def test_update_api_key_scopes():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()
    target_key, _ = create_test_key()

    try:
        response = TestClient(app).put(
            f"/api-keys/{target_key.key_id}/scopes",
            json={
                "scopes": [
                    "workers:read",
                    "executions:read",
                ],
            },
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["key_id"] == target_key.key_id
        assert data["scopes"] == [
            "executions:read",
            "workers:read",
        ]

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )
        api_key_service.delete_api_key(
            target_key.key_id
        )


def test_get_api_key_returns_scopes():
    app = FastAPI()
    app.include_router(router)

    bootstrap_key, bootstrap_raw_key = create_test_key()
    target_key, _ = api_key_service.create_api_key(
        "scope-get-test",
        scopes=[
            "workflows:read",
        ],
    )

    try:
        response = TestClient(app).get(
            f"/api-keys/{target_key.key_id}",
            headers={
                "Authorization": f"Bearer {bootstrap_raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["key_id"] == target_key.key_id
        assert data["scopes"] == [
            "workflows:read",
        ]

    finally:
        api_key_service.delete_api_key(
            bootstrap_key.key_id
        )
        api_key_service.delete_api_key(
            target_key.key_id
        )