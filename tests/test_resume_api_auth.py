from fastapi.testclient import TestClient

from app.api.workflows import runtime
from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


client = TestClient(app)

repository = APIKeyRepository(SessionLocal)
service = APIKeyService(repository)


def test_resume_requires_api_key():
    response = client.post(
        "/workflows/executions/resume-auth-test/resume",
    )

    assert response.status_code == 401


def test_resume_rejects_invalid_api_key():
    response = client.post(
        "/workflows/executions/resume-auth-test/resume",
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401


def test_resume_accepts_valid_api_key(monkeypatch):
    api_key, raw_key = service.create_api_key(
        "resume-auth-test"
    )

    class FakeExecution:
        execution_id = "resume-auth-test"
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

    def fake_resume_execution(execution_id):
        assert execution_id == "resume-auth-test"
        return FakeExecution()

    monkeypatch.setattr(
        runtime,
        "resume_execution",
        fake_resume_execution,
    )

    try:
        response = client.post(
            "/workflows/executions/resume-auth-test/resume",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "execution_id": "resume-auth-test",
            "workflow": "research-pipeline",
            "status": "running",
            "step_statuses": {},
            "step_results": {},
        }
    finally:
        service.delete_api_key(api_key.key_id)