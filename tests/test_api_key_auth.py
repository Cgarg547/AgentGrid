from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.security.api_key_auth import require_api_key
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


app = FastAPI()


@app.get("/protected")
def protected(api_key=Depends(require_api_key)):
    return {
        "authenticated": True,
        "name": api_key.name,
    }


client = TestClient(app)

repository = APIKeyRepository(SessionLocal)
service = APIKeyService(repository)


def test_missing_api_key_is_rejected():
    response = client.get("/protected")

    assert response.status_code == 401


def test_invalid_api_key_is_rejected():
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401


def test_valid_api_key_is_accepted():
    api_key, raw_key = service.create_api_key("auth-test")

    try:
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "authenticated": True,
            "name": "auth-test",
        }
    finally:
        service.delete_api_key(api_key.key_id)


def test_disabled_api_key_is_rejected():
    api_key, raw_key = service.create_api_key("disabled-auth-test")

    try:
        service.disable_api_key(api_key.key_id)

        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 401
    finally:
        service.delete_api_key(api_key.key_id)