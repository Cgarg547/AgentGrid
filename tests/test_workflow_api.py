from fastapi.testclient import TestClient

from app.api.workflows import router


def test_distributed_workflow_api_starts_execution():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    response = client.post(
        "/workflows/research-pipeline/execute/distributed",
        json={
            "inputs": {
                "topic": "AI orchestration",
            }
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["execution_id"]
    assert data["workflow"] == "research-pipeline"
    assert data["status"] == "running"
    assert data["step_results"] == {}