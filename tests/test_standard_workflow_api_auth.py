from fastapi.testclient import TestClient

from app.api.workflows import runtime
from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


client = TestClient(app)

repository = APIKeyRepository(SessionLocal)
service = APIKeyService(repository)


def test_standard_workflow_execution_requires_api_key():
    response = client.post(
        "/workflows/research-pipeline/execute",
    )

    assert response.status_code == 401


def test_standard_workflow_execution_rejects_invalid_api_key():
    response = client.post(
        "/workflows/research-pipeline/execute",
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401


def test_standard_workflow_execution_accepts_valid_api_key(monkeypatch):
    api_key, raw_key = service.create_api_key(
        "standard-workflow-auth-test"
    )

    class FakeExecution:
        execution_id = "standard-auth-test-execution"
        status = type(
            "Status",
            (),
            {"value": "running"},
        )()
        step_results = {}

    def fake_execute_workflow(workflow_name):
        assert workflow_name == "research-pipeline"
        return FakeExecution()

    monkeypatch.setattr(
        runtime,
        "execute_workflow",
        fake_execute_workflow,
    )

    try:
        response = client.post(
            "/workflows/research-pipeline/execute",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "execution_id": "standard-auth-test-execution",
            "workflow": "research-pipeline",
            "status": "running",
            "step_results": {},
        }
    finally:
        service.delete_api_key(api_key.key_id)