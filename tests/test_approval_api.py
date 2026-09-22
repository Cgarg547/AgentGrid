import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.security.approval import ApprovalRequest
from app.security.approval_store import ApprovalStore
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


client = TestClient(app)

api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def create_test_request():
    request_id = f"api-test-{uuid.uuid4()}"

    store = ApprovalStore()

    request = ApprovalRequest(
        request_id=request_id,
        agent_name="researcher",
        tool_name="send_email",
        arguments={
            "to": "test@example.com",
            "subject": "AgentGrid test",
        },
    )

    store.save(request)

    return store, request_id


def create_test_key(scopes):
    return api_key_service.create_api_key(
        "approval-api-test",
        scopes=scopes,
    )


def auth_headers(raw_key):
    return {
        "Authorization": f"Bearer {raw_key}"
    }


def test_get_approval_request():
    store, request_id = create_test_request()

    test_key, raw_key = create_test_key(
        ["executions:read"]
    )

    try:
        response = client.get(
            f"/approvals/{request_id}",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload == {
            "request_id": request_id,
            "agent_name": "researcher",
            "tool_name": "send_email",
            "status": "pending",
        }

    finally:
        store.delete(request_id)
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_approve_request():
    store, request_id = create_test_request()

    test_key, raw_key = create_test_key(
        ["executions:control"]
    )

    try:
        response = client.post(
            f"/approvals/{request_id}/approve",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["request_id"] == request_id
        assert payload["status"] == "approved"

        assert payload["execution_result"] == {
            "message": "email sent",
            "arguments": {
                "to": "test@example.com",
                "subject": "AgentGrid test",
            },
        }

        stored = store.get(request_id)

        assert stored is not None
        assert stored.status.value == "approved"
        assert stored.arguments == {
            "to": "test@example.com",
            "subject": "AgentGrid test",
        }

    finally:
        store.delete(request_id)
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_reject_request():
    store, request_id = create_test_request()

    test_key, raw_key = create_test_key(
        ["executions:control"]
    )

    try:
        response = client.post(
            f"/approvals/{request_id}/reject",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["request_id"] == request_id
        assert payload["status"] == "rejected"

        stored = store.get(request_id)

        assert stored is not None
        assert stored.status.value == "rejected"

    finally:
        store.delete(request_id)
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_get_unknown_approval_request():
    request_id = f"missing-{uuid.uuid4()}"

    test_key, raw_key = create_test_key(
        ["executions:read"]
    )

    try:
        response = client.get(
            f"/approvals/{request_id}",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 404

    finally:
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_approve_unknown_request():
    request_id = f"missing-{uuid.uuid4()}"

    test_key, raw_key = create_test_key(
        ["executions:control"]
    )

    try:
        response = client.post(
            f"/approvals/{request_id}/approve",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 404

    finally:
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_reject_unknown_request():
    request_id = f"missing-{uuid.uuid4()}"

    test_key, raw_key = create_test_key(
        ["executions:control"]
    )

    try:
        response = client.post(
            f"/approvals/{request_id}/reject",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 404

    finally:
        api_key_service.delete_api_key(
            test_key.key_id
        )

def test_approval_api_enforces_rate_limit(monkeypatch):
    import app.security.rate_limit as rate_limit_module

    monkeypatch.setattr(
        rate_limit_module,
        "RATE_LIMIT",
        1,
    )

    test_key, raw_key = create_test_key(
        ["executions:read"]
    )

    try:
        response = client.get(
            "/approvals/nonexistent-request",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 404

        response = client.get(
            "/approvals/nonexistent-request",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 429

    finally:
        api_key_service.delete_api_key(
            test_key.key_id
        )