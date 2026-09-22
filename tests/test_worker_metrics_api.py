from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app
from app.api.metrics import get_worker_metrics
from app.core.database import SessionLocal
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.workers.dead_letter import DeadLetterQueue
from app.workers.heartbeat import WorkerHeartbeatRegistry
from app.workers.metrics import WorkerMetrics
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def create_test_metrics() -> WorkerMetrics:
    test_id = uuid4().hex

    return WorkerMetrics(
        task_queue=TaskQueue(
            f"test:api:metrics:tasks:(test_id)"
        ),
        result_queue=TaskResultQueue(
            f"test:api:metrics:results:(test_id)"
        ),
        dead_letter_queue=DeadLetterQueue(
            f"test:api:metrics:dead-letter:{test_id}"
        ),
        heartbeat_registry=WorkerHeartbeatRegistry(
            key_prefix=f"test:api:metrics:workers:{test_id}"
        ),
    )


def create_test_key():
    return api_key_service.create_api_key(
        "worker-metrics-api-test",
        scopes=[
            "workers:read",
        ],
    )


def auth_headers(raw_key: str):
    return {
        "Authorization": f"Bearer {raw_key}"
    }


def test_queue_metrics_api():
    metrics = create_test_metrics()

    app.dependency_overrides[
        get_worker_metrics
    ] = lambda: metrics

    test_key, raw_key = create_test_key()

    try:
        client = TestClient(app)

        response = client.get(
            "/metrics/queues",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200
        assert response.json() == {
            "tasks": 0,
            "results": 0,
            "dead_letter": 0,
        }

    finally:
        app.dependency_overrides.clear()
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_worker_metrics_api():
    metrics = create_test_metrics()

    metrics.heartbeat_registry.register(
        worker_id="api-worker"
    )

    app.dependency_overrides[
        get_worker_metrics
    ] = lambda: metrics

    test_key, raw_key = create_test_key()

    try:
        client = TestClient(app)

        response = client.get(
            "/metrics/workers",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200
        assert response.json() == {
            "total": 1,
            "idle": 1,
            "running": 0,
            "utilization": 0.0,
        }

    finally:
        metrics.heartbeat_registry.unregister(
            "api-worker"
        )
        app.dependency_overrides.clear()
        api_key_service.delete_api_key(
            test_key.key_id
        )


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

    test_key, raw_key = create_test_key()

    try:
        client = TestClient(app)

        response = client.get(
            "/metrics",
            headers=auth_headers(raw_key),
        )

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

    finally:
        app.dependency_overrides.clear()
        api_key_service.delete_api_key(
            test_key.key_id
        )

def test_metrics_api_enforces_rate_limit():
    import fakeredis
    import app.security.rate_limit as rate_limit_module

    test_key, raw_key = create_test_key()

    fake_redis = fakeredis.FakeRedis()

    original_get_redis_client = rate_limit_module.get_redis_client
    original_rate_limit = rate_limit_module.RATE_LIMIT

    rate_limit_module.get_redis_client = lambda: fake_redis
    rate_limit_module.RATE_LIMIT = 1

    try:
        client = TestClient(app)

        first_response = client.get(
            "/metrics/queues",
            headers=auth_headers(raw_key),
        )

        second_response = client.get(
            "/metrics/queues",
            headers=auth_headers(raw_key),
        )

    finally:
        rate_limit_module.get_redis_client = original_get_redis_client
        rate_limit_module.RATE_LIMIT = original_rate_limit

        api_key_service.delete_api_key(
            test_key.key_id
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == "Rate limit exceeded."
    assert second_response.headers["Retry-After"] == "60"