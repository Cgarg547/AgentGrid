from fastapi.testclient import TestClient

from app.api.workflows import runtime
from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


client = TestClient(app)

repository = APIKeyRepository(SessionLocal)
service = APIKeyService(repository)


def test_pause_requires_api_key():
    response = client.post(
        "/workflows/executions/pause-auth-test/pause",
    )

    assert response.status_code == 401


def test_pause_rejects_invalid_api_key():
    response = client.post(
        "/workflows/executions/pause-auth-test/pause",
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401


def test_pause_accepts_valid_api_key(monkeypatch):
    api_key, raw_key = service.create_api_key(
        "pause-auth-test"
    )

    class FakeExecution:
        execution_id = "pause-auth-test"
        workflow = type(
            "Workflow",
            (),
            {"name": "research-pipeline"},
        )()
        status = type(
            "Status",
            (),
            {"value": "paused"},
        )()
        step_statuses = {}
        step_results = {}

    def fake_pause_execution(execution_id):
        assert execution_id == "pause-auth-test"
        return FakeExecution()

    monkeypatch.setattr(
        runtime,
        "pause_execution",
        fake_pause_execution,
    )

    try:
        response = client.post(
            "/workflows/executions/pause-auth-test/pause",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "execution_id": "pause-auth-test",
            "workflow": "research-pipeline",
            "status": "paused",
            "step_statuses": {},
            "step_results": {},
        }
    finally:
        service.delete_api_key(api_key.key_id)