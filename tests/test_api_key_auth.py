from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.security.api_key_auth import require_api_key
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.services.security_audit_repository import SecurityAuditRepository


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

audit_repository = SecurityAuditRepository(SessionLocal)


def get_authentication_events():
    return audit_repository.list(
        action="authentication",
    )


def test_missing_api_key_is_rejected():
    response = client.get("/protected")

    assert response.status_code == 401

    events = get_authentication_events()

    assert events

    event = events[-1]

    assert event.key_id is None
    assert event.action == "authentication"
    assert event.outcome == "denied"

    metadata = (
        SecurityAuditRepository.deserialize_metadata(
            event.metadata_json
        )
    )

    assert metadata["reason"] == "missing_api_key"


def test_invalid_api_key_is_rejected():
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401

    events = get_authentication_events()

    assert events

    event = events[-1]

    assert event.key_id is None
    assert event.action == "authentication"
    assert event.outcome == "denied"

    metadata = (
        SecurityAuditRepository.deserialize_metadata(
            event.metadata_json
        )
    )

    assert metadata["reason"] == (
        "invalid_or_disabled_api_key"
    )


def test_valid_api_key_is_accepted():
    api_key, raw_key = service.create_api_key(
        "auth-test"
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
            "authenticated": True,
            "name": "auth-test",
        }

        events = get_authentication_events()

        matching_events = [
            event
            for event in events
            if event.key_id == api_key.key_id
            and event.outcome == "allowed"
        ]

        assert matching_events

        event = matching_events[-1]

        assert event.action == "authentication"
        assert event.key_id == api_key.key_id

    finally:
        service.delete_api_key(api_key.key_id)


def test_disabled_api_key_is_rejected():
    api_key, raw_key = service.create_api_key(
        "disabled-auth-test"
    )

    try:
        service.disable_api_key(
            api_key.key_id
        )

        response = client.get(
            "/protected",
            headers={
                "Authorization": f"Bearer {raw_key}"
            },
        )

        assert response.status_code == 401

        events = get_authentication_events()

        matching_events = [
            event
            for event in events
            if event.key_id is None
            and event.action == "authentication"
            and event.outcome == "denied"
        ]

        assert matching_events

        event = matching_events[-1]

        metadata = (
            SecurityAuditRepository.deserialize_metadata(
                event.metadata_json
            )
        )

        assert metadata["reason"] == (
            "invalid_or_disabled_api_key"
        )

    finally:
        service.delete_api_key(api_key.key_id)