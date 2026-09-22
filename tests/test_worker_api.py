from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.workers import worker_registry
from app.main import app


client = TestClient(app)


def test_list_workers_returns_workers():
    worker_id = f"worker-api-{uuid4()}"

    worker_registry.register(
        worker_id,
        metadata={
            "hostname": "api-test-worker",
        },
    )

    response = client.get("/workers")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] >= 1

    workers = [
        worker
        for worker in data["workers"]
        if worker["worker_id"] == worker_id
    ]

    assert len(workers) == 1
    assert workers[0]["state"] == "idle"


def test_get_worker_returns_worker():
    worker_id = f"worker-api-detail-{uuid4()}"

    worker_registry.register(
        worker_id,
        metadata={
            "hostname": "api-test-worker",
        },
    )

    response = client.get(
        f"/workers/{worker_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["worker_id"] == worker_id
    assert data["status"] == "alive"
    assert data["state"] == "idle"
    assert data["metadata"]["hostname"] == (
        "api-test-worker"
    )


def test_get_unknown_worker_returns_404():
    worker_id = f"unknown-worker-{uuid4()}"

    response = client.get(
        f"/workers/{worker_id}"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == (
        f"Worker '{worker_id}' not found."
    )


def test_worker_api_reflects_running_state():
    worker_id = f"worker-api-running-{uuid4()}"

    worker_registry.register(worker_id)

    worker_registry.set_state(
        worker_id,
        "running",
        metadata={
            "task_id": "task-123",
        },
    )

    response = client.get(
        f"/workers/{worker_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["state"] == "running"
    assert data["metadata"]["task_id"] == (
        "task-123"
    )


def test_worker_api_lists_multiple_workers():
    worker_a = f"worker-api-a-{uuid4()}"
    worker_b = f"worker-api-b-{uuid4()}"

    worker_registry.register(worker_a)
    worker_registry.register(worker_b)

    response = client.get("/workers")

    assert response.status_code == 200

    data = response.json()

    worker_ids = {
        worker["worker_id"]
        for worker in data["workers"]
    }

    assert worker_a in worker_ids
    assert worker_b in worker_ids
