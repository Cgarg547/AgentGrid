from fastapi.testclient import TestClient

from app.api.workflows import runtime
from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


client = TestClient(app)

repository = APIKeyRepository(SessionLocal)
service = APIKeyService(repository)


def test_execution_status_requires_api_key():
    response = client.get(
        "/workflows/executions/nonexistent-execution",
    )

    assert response.status_code == 401


def test_execution_status_rejects_invalid_api_key():
    response = client.get(
        "/workflows/executions/nonexistent-execution",
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401


def test_execution_status_accepts_valid_api_key(monkeypatch):
    api_key, raw_key = service.create_api_key(
        "execution-status-auth-test"
    )

    class FakeExecution:
        execution_id = "status-auth-test-execution"
        workflow = type(
            "Workflow",
            (),
            {"name": "research-pipeline"},
        )()
        status = type(
            "Status",
            (),
            {"value": "running"},
        )()
        step_statuses = {}
        step_results = {}

    def fake_get_execution(execution_id):
        assert execution_id == "status-auth-test-execution"
        return FakeExecution()

    monkeypatch.setattr(
        runtime,
        "get_execution",
        fake_get_execution,
    )

    try:
        response = client.get(
            "/workflows/executions/status-auth-test-execution",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "execution_id": "status-auth-test-execution",
            "workflow": "research-pipeline",
            "status": "running",
            "step_statuses": {},
            "step_results": {},
        }
    finally:
        service.delete_api_key(api_key.key_id)