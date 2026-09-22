from uuid import uuid4

from app.workers.heartbeat import WorkerHeartbeatRegistry


def create_registry() -> WorkerHeartbeatRegistry:
    return WorkerHeartbeatRegistry(
        key_prefix=f"test-agentgrid-workers-{uuid4()}",
        heartbeat_ttl_seconds=5,
    )


def test_worker_registry_lists_registered_workers():
    registry = create_registry()

    registry.register(
        "worker-a",
        metadata={"state": "idle"},
    )

    registry.register(
        "worker-b",
        metadata={"state": "running"},
    )

    workers = registry.list_workers()

    assert len(workers) == 2

    worker_ids = {
        worker["worker_id"]
        for worker in workers
    }

    assert worker_ids == {
        "worker-a",
        "worker-b",
    }


def test_worker_registry_returns_worker_count():
    registry = create_registry()

    assert registry.count_workers() == 0

    registry.register("worker-a")
    registry.register("worker-b")

    assert registry.count_workers() == 2


def test_worker_registry_returns_worker_details():
    registry = create_registry()

    registry.register(
        "worker-details",
        metadata={
            "hostname": "agentgrid-worker-1",
            "state": "idle",
        },
    )

    worker = registry.get("worker-details")

    assert worker is not None
    assert worker["worker_id"] == "worker-details"
    assert worker["status"] == "alive"
    assert worker["state"] == "idle"
    assert worker["metadata"]["hostname"] == (
        "agentgrid-worker-1"
    )


def test_worker_registry_updates_worker_state():
    registry = create_registry()

    registry.register("worker-state")

    assert registry.set_state(
        "worker-state",
        "running",
    ) is True

    worker = registry.get("worker-state")

    assert worker is not None
    assert worker["state"] == "running"


def test_worker_registry_heartbeat_updates_state():
    registry = create_registry()

    registry.register("worker-heartbeat")

    assert registry.heartbeat(
        "worker-heartbeat",
        state="running",
        metadata={
            "task_id": "task-123",
        },
    ) is True

    worker = registry.get("worker-heartbeat")

    assert worker is not None
    assert worker["state"] == "running"
    assert worker["metadata"]["task_id"] == "task-123"


def test_worker_registry_removes_unregistered_worker():
    registry = create_registry()

    registry.register("worker-remove")

    assert registry.count_workers() == 1

    assert registry.unregister(
        "worker-remove"
    ) is True

    assert registry.count_workers() == 0


def test_worker_registry_returns_false_for_unknown_state():
    registry = create_registry()

    assert registry.set_state(
        "unknown-worker",
        "running",
    ) is False
