import uuid
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.api.workflows import runtime
from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.security.rate_limit import (
    RATE_LIMIT,
)


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

        def list_by_execution_id(self, execution_id):
            assert execution_id == "events-auth-test"
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

def test_execution_trace_requires_api_key():
    execution_id = str(uuid.uuid4())

    response = client.get(
        f"/workflows/executions/{execution_id}/trace"
    )

    assert response.status_code == 401


def test_execution_trace_rejects_invalid_api_key():
    execution_id = str(uuid.uuid4())

    response = client.get(
        f"/workflows/executions/{execution_id}/trace",
        headers={
            "Authorization": "Bearer invalid-key",
        },
    )

    assert response.status_code == 401

def test_execution_trace_accepts_valid_api_key():
    api_key, raw_key = service.create_api_key(
        "execution-trace-auth-test"
    )

    execution_id = str(uuid.uuid4())

    try:
        response = client.get(
            f"/workflows/executions/{execution_id}/trace",
            headers={
                "Authorization": f"Bearer {raw_key}",
            },
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["execution_id"] == execution_id
        assert payload["tasks"] == []

    finally:
        service.delete_api_key(api_key.key_id)

def test_execution_trace_enforces_rate_limit():
    import fakeredis
    import app.security.rate_limit as rate_limit_module

    api_key, raw_key = service.create_api_key(
        "execution-trace-rate-limit-test"
    )

    fake_redis = fakeredis.FakeRedis()

    original_get_redis_client = (
        rate_limit_module.get_redis_client
    )
    original_rate_limit = rate_limit_module.RATE_LIMIT

    rate_limit_module.get_redis_client = (
        lambda: fake_redis
    )
    rate_limit_module.RATE_LIMIT = 1

    execution_id = str(uuid.uuid4())

    try:
        first_response = client.get(
            f"/workflows/executions/{execution_id}/trace",
            headers={
                "Authorization": f"Bearer {raw_key}",
            },
        )

        second_response = client.get(
            f"/workflows/executions/{execution_id}/trace",
            headers={
                "Authorization": f"Bearer {raw_key}",
            },
        )

    finally:
        rate_limit_module.get_redis_client = (
            original_get_redis_client
        )
        rate_limit_module.RATE_LIMIT = (
            original_rate_limit
        )

        service.delete_api_key(api_key.key_id)

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == (
        "Rate limit exceeded."
    )
    assert second_response.headers["Retry-After"] == "60"