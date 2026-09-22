from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.security.scope_auth import require_scope
from app.security.scopes import APIScope
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def test_scope_authorization_allows_required_scope():
    app = FastAPI()

    @app.get(
        "/protected",
        dependencies=[
            Depends(
                require_scope(
                    APIScope.WORKFLOWS_EXECUTE
                )
            )
        ],
    )
    def protected():
        return {"status": "allowed"}

    client = TestClient(app)

    api_key, raw_key = api_key_service.create_api_key(
        "scope-auth-allowed",
        scopes=[
            "workflows:execute",
        ],
    )

    try:
        response = client.get(
            "/protected",
            headers={
                "Authorization": f"Bearer {raw_key}"
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "allowed"
        }

    finally:
        api_key_service.delete_api_key(
            api_key.key_id
        )


def test_scope_authorization_rejects_missing_scope():
    app = FastAPI()

    @app.get(
        "/protected",
        dependencies=[
            Depends(
                require_scope(
                    APIScope.WORKFLOWS_EXECUTE
                )
            )
        ],
    )
    def protected():
        return {"status": "allowed"}

    client = TestClient(app)

    api_key, raw_key = api_key_service.create_api_key(
        "scope-auth-denied",
        scopes=[
            "workflows:read",
        ],
    )

    try:
        response = client.get(
            "/protected",
            headers={
                "Authorization": f"Bearer {raw_key}"
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "Missing required scope: workflows:execute"
        )

    finally:
        api_key_service.delete_api_key(
            api_key.key_id
        )


def test_scope_authorization_still_requires_api_key():
    app = FastAPI()

    @app.get(
        "/protected",
        dependencies=[
            Depends(
                require_scope(
                    APIScope.WORKFLOWS_EXECUTE
                )
            )
        ],
    )
    def protected():
        return {"status": "allowed"}

    client = TestClient(app)

    response = client.get("/protected")

    assert response.status_code == 401