from fastapi.testclient import TestClient

from app.main import app
from app.api.metrics import get_worker_metrics
from app.workers.dead_letter import DeadLetterQueue
from app.workers.heartbeat import WorkerHeartbeatRegistry
from app.workers.metrics import WorkerMetrics
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue


def create_test_metrics() -> WorkerMetrics:
    return WorkerMetrics(
        task_queue=TaskQueue(
            "test:api:metrics:tasks"
        ),
        result_queue=TaskResultQueue(
            "test:api:metrics:results"
        ),
        dead_letter_queue=DeadLetterQueue(
            "test:api:metrics:dead-letter"
        ),
        heartbeat_registry=WorkerHeartbeatRegistry(
            key_prefix="test:api:metrics:workers"
        ),
    )


def test_queue_metrics_api():
    metrics = create_test_metrics()

    app.dependency_overrides[
        get_worker_metrics
    ] = lambda: metrics

    client = TestClient(app)

    response = client.get("/metrics/queues")

    assert response.status_code == 200
    assert response.json() == {
        "tasks": 0,
        "results": 0,
        "dead_letter": 0,
    }

    app.dependency_overrides.clear()


def test_worker_metrics_api():
    metrics = create_test_metrics()

    metrics.heartbeat_registry.register(
        worker_id="api-worker"
    )

    app.dependency_overrides[
        get_worker_metrics
    ] = lambda: metrics

    client = TestClient(app)

    response = client.get("/metrics/workers")

    assert response.status_code == 200
    assert response.json() == {
        "total": 1,
        "idle": 1,
        "running": 0,
        "utilization": 0.0,
    }

    metrics.heartbeat_registry.unregister(
        "api-worker"
    )

    app.dependency_overrides.clear()


def test_metrics_snapshot_api():
    metrics = create_test_metrics()

    metrics.task_queue.enqueue({
        "task_id": "api-task",
    })

    metrics.result_queue.publish({
        "task_id": "api-result",
        "status": "completed",
    })

    app.dependency_overrides[
        get_worker_metrics
    ] = lambda: metrics

    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200

    assert response.json() == {
        "queues": {
            "tasks": 1,
            "results": 1,
            "dead_letter": 0,
        },
        "workers": {
            "total": 0,
            "idle": 0,
            "running": 0,
            "utilization": 0.0,
        },
    }

    metrics.task_queue.dequeue()
    metrics.result_queue.consume()

    app.dependency_overrides.clear()