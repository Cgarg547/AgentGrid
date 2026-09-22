from fastapi.testclient import TestClient

from app.api.workflows import router, runtime
from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.services.security_audit_repository import (
    SecurityAuditRepository,
)

client = TestClient(app)

repository = APIKeyRepository(SessionLocal)
service = APIKeyService(repository)

audit_repository = SecurityAuditRepository(
    SessionLocal
)


def test_distributed_workflow_requires_api_key():
    response = client.post(
        "/workflows/research-pipeline/execute/distributed",
        json={"inputs": {}},
    )

    assert response.status_code == 401


def test_distributed_workflow_rejects_invalid_api_key():
    response = client.post(
        "/workflows/research-pipeline/execute/distributed",
        json={"inputs": {}},
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401


def test_distributed_workflow_accepts_valid_api_key(monkeypatch):
    api_key, raw_key = service.create_api_key(
        "workflow-api-auth-test"
    )

    class FakeExecution:
        execution_id = "auth-test-execution"
        status = type(
            "Status",
            (),
            {"value": "running"},
        )()
        step_results = {}

    def fake_execute_workflow_distributed(
        workflow_name,
        inputs=None,
    ):
        assert workflow_name == "research-pipeline"
        assert inputs == {}
        return FakeExecution()

    monkeypatch.setattr(
        runtime,
        "execute_workflow_distributed",
        fake_execute_workflow_distributed,
    )

    try:
        response = client.post(
            "/workflows/research-pipeline/execute/distributed",
            json={"inputs": {}},
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "execution_id": "auth-test-execution",
            "workflow": "research-pipeline",
            "status": "running",
            "step_results": {},
        }

        events = audit_repository.list(
            key_id=api_key.key_id,
            action="workflow.execute.distributed",
        )

        assert events

        event = events[-1]

        assert event.resource == "research-pipeline"

        assert event.endpoint == (
            "POST "
            "/workflows/{workflow_name}/execute/distributed"
        )

        assert event.outcome == "allowed"

        metadata = (
            SecurityAuditRepository.deserialize_metadata(
                event.metadata_json
            )
        )

        assert metadata["execution_id"] == (
            "auth-test-execution"
        )

    finally:
        service.delete_api_key(api_key.key_id)