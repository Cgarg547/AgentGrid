from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.api.workflows import runtime
from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


client = TestClient(app)

repository = APIKeyRepository(SessionLocal)
service = APIKeyService(repository)


def test_execution_events_requires_api_key():
    response = client.get(
        "/workflows/executions/events-auth-test/events",
    )

    assert response.status_code == 401


def test_execution_events_rejects_invalid_api_key():
    response = client.get(
        "/workflows/executions/events-auth-test/events",
        headers={"Authorization": "Bearer ag_invalid_key"},
    )

    assert response.status_code == 401


def test_execution_events_accepts_valid_api_key(monkeypatch):
    api_key, raw_key = service.create_api_key(
        "execution-events-auth-test"
    )

    class FakeEvent:
        id = 1
        task_id = "events-auth-test"
        event_type = "task.completed"
        timestamp = datetime.now(timezone.utc)
        data = "{}"

    class FakeRepository:
        def __init__(self, session):
            self.session = session

        def list_by_task(self, task_id):
            assert task_id == "events-auth-test"
            return [FakeEvent()]

        @staticmethod
        def deserialize_data(data):
            return {}

    monkeypatch.setattr(
        "app.api.workflows.ExecutionEventRepository",
        FakeRepository,
    )

    try:
        response = client.get(
            "/workflows/executions/events-auth-test/events",
            headers={"Authorization": f"Bearer {raw_key}"},
        )

        assert response.status_code == 200
        assert response.json()["task_id"] == "events-auth-test"
        assert len(response.json()["events"]) == 1
        assert response.json()["events"][0]["event_type"] == "task.completed"
    finally:
        service.delete_api_key(api_key.key_id)