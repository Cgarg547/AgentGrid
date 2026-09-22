from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.workflows import router
from app.core.database import SessionLocal
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def test_distributed_workflow_api_starts_execution():
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    api_key, raw_key = api_key_service.create_api_key(
        "workflow-api-test"
    )

    try:
        response = client.post(
            "/workflows/research-pipeline/execute/distributed",
            json={
                "inputs": {
                    "topic": "AI orchestration",
                }
            },
            headers={
                "Authorization": f"Bearer {raw_key}"
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["execution_id"]
        assert data["workflow"] == "research-pipeline"
        assert data["status"] == "running"
        assert data["step_results"] == {}

    finally:
        api_key_service.delete_api_key(
            api_key.key_id
        )

def test_distributed_workflow_api_enforces_rate_limit():
    import fakeredis
    import app.security.rate_limit as rate_limit_module

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    api_key, raw_key = api_key_service.create_api_key(
        "workflow-rate-limit-test"
    )

    fake_redis = fakeredis.FakeRedis()

    original_get_redis_client = rate_limit_module.get_redis_client
    original_rate_limit = rate_limit_module.RATE_LIMIT

    rate_limit_module.get_redis_client = lambda: fake_redis
    rate_limit_module.RATE_LIMIT = 1

    try:
        first_response = client.post(
            "/workflows/research-pipeline/execute/distributed",
            json={
                "inputs": {
                    "topic": "AI orchestration",
                }
            },
            headers={
                "Authorization": f"Bearer {raw_key}"
            },
        )

        second_response = client.post(
            "/workflows/research-pipeline/execute/distributed",
            json={
                "inputs": {
                    "topic": "AI orchestration",
                }
            },
            headers={
                "Authorization": f"Bearer {raw_key}"
            },
        )

    finally:
        rate_limit_module.get_redis_client = original_get_redis_client
        rate_limit_module.RATE_LIMIT = original_rate_limit

        api_key_service.delete_api_key(
            api_key.key_id
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == "Rate limit exceeded."
    assert second_response.headers["Retry-After"] == "60"