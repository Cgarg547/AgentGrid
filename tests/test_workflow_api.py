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