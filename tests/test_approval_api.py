import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.security.approval import ApprovalRequest
from app.security.approval_store import ApprovalStore


client = TestClient(app)

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

def test_get_approval_request():
    store, request_id = create_test_request()

    try:
        response = client.get(
            f"/approvals/{request_id}"
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


def test_approve_request():
    store, request_id = create_test_request()

    try:
        response = client.post(
            f"/approvals/{request_id}/approve"
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


def test_reject_request():
    store, request_id = create_test_request()

    try:
        response = client.post(
            f"/approvals/{request_id}/reject"
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


def test_get_unknown_approval_request():
    request_id = f"missing-{uuid.uuid4()}"

    response = client.get(
        f"/approvals/{request_id}"
    )

    assert response.status_code == 404


def test_approve_unknown_request():
    request_id = f"missing-{uuid.uuid4()}"

    response = client.post(
        f"/approvals/{request_id}/approve"
    )

    assert response.status_code == 404


def test_reject_unknown_request():
    request_id = f"missing-{uuid.uuid4()}"

    response = client.post(
        f"/approvals/{request_id}/reject"
    )

    assert response.status_code == 404