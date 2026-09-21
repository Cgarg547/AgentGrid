import time
from uuid import uuid4

from app.workers.heartbeat import WorkerHeartbeatRegistry


def test_worker_heartbeat_registers_worker():
    registry = WorkerHeartbeatRegistry(
        key_prefix=f"test-agentgrid-workers-{uuid4()}",
        heartbeat_ttl_seconds=5,
    )

    worker_id = "worker-test"

    registered_id = registry.register(
        worker_id=worker_id,
        metadata={
            "hostname": "test-host",
        },
    )

    assert registered_id == worker_id

    record = registry.get(worker_id)

    assert record is not None
    assert record["worker_id"] == worker_id
    assert record["status"] == "alive"
    assert record["metadata"] == {
        "hostname": "test-host",
    }


def test_worker_heartbeat_marks_worker_alive():
    registry = WorkerHeartbeatRegistry(
        key_prefix=f"test-agentgrid-workers-{uuid4()}",
        heartbeat_ttl_seconds=5,
    )

    worker_id = "worker-heartbeat"

    registry.register(worker_id)

    assert registry.is_alive(worker_id) is True

    assert registry.heartbeat(
        worker_id,
        metadata={
            "state": "running",
        },
    ) is True

    record = registry.get(worker_id)

    assert record is not None
    assert record["status"] == "alive"
    assert record["metadata"] == {
        "state": "running",
    }


def test_worker_heartbeat_expires_stale_worker():
    registry = WorkerHeartbeatRegistry(
        key_prefix=f"test-agentgrid-workers-{uuid4()}",
        heartbeat_ttl_seconds=1,
    )

    worker_id = "worker-stale"

    registry.register(worker_id)

    assert registry.is_alive(worker_id) is True

    time.sleep(1.1)

    assert registry.is_alive(worker_id) is False


def test_worker_heartbeat_returns_false_for_unknown_worker():
    registry = WorkerHeartbeatRegistry(
        key_prefix=f"test-agentgrid-workers-{uuid4()}",
        heartbeat_ttl_seconds=5,
    )

    assert registry.heartbeat(
        "unknown-worker"
    ) is False


def test_worker_heartbeat_unregisters_worker():
    registry = WorkerHeartbeatRegistry(
        key_prefix=f"test-agentgrid-workers-{uuid4()}",
        heartbeat_ttl_seconds=5,
    )

    worker_id = "worker-unregister"

    registry.register(worker_id)

    assert registry.is_alive(worker_id) is True

    assert registry.unregister(worker_id) is True

    assert registry.is_alive(worker_id) is False