from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.security.scope_auth import require_scope
from app.security.scopes import APIScope
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.services.security_audit_repository import SecurityAuditRepository


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)

audit_repository = SecurityAuditRepository(
    SessionLocal
)


def get_authorization_events():
    return audit_repository.list(
        action="authorization",
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

        events = get_authorization_events()

        matching_events = [
            event
            for event in events
            if event.key_id == api_key.key_id
            and event.outcome == "allowed"
        ]

        assert matching_events

        event = matching_events[-1]

        assert event.action == "authorization"

        metadata = (
            SecurityAuditRepository.deserialize_metadata(
                event.metadata_json
            )
        )

        assert metadata["required_scope"] == (
            "workflows:execute"
        )

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
            "Missing required scope: "
            "workflows:execute"
        )

        events = get_authorization_events()

        matching_events = [
            event
            for event in events
            if event.key_id == api_key.key_id
            and event.outcome == "denied"
        ]

        assert matching_events

        event = matching_events[-1]

        assert event.action == "authorization"

        metadata = (
            SecurityAuditRepository.deserialize_metadata(
                event.metadata_json
            )
        )

        assert metadata["required_scope"] == (
            "workflows:execute"
        )

        assert metadata["reason"] == (
            "missing_required_scope"
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