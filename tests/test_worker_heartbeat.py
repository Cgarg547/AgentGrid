import time
from uuid import uuid4
import threading
from app.workers.queue import TaskQueue
from app.workers.worker import Worker
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

def test_worker_keeps_idle_heartbeat_alive():
    heartbeat_registry = WorkerHeartbeatRegistry(
        key_prefix="test:idle:heartbeat:workers",
        heartbeat_ttl_seconds=1,
    )

    worker = Worker(
        queue=TaskQueue(
            "test:idle:heartbeat:queue"
        ),
        agent_handlers={},
        heartbeat_registry=heartbeat_registry,
    )

    try:
        assert heartbeat_registry.is_alive(
            worker.owner_id
        )

        time.sleep(1.5)

        assert heartbeat_registry.is_alive(
            worker.owner_id
        )
    finally:
        worker.stop()

def test_worker_stop_stops_lifecycle_heartbeat_and_unregisters():
    heartbeat_registry = WorkerHeartbeatRegistry(
        key_prefix="test:stop:heartbeat:workers",
        heartbeat_ttl_seconds=1,
    )

    worker = Worker(
        queue=TaskQueue(
            "test:stop:heartbeat:queue"
        ),
        agent_handlers={},
        heartbeat_registry=heartbeat_registry,
    )

    worker_id = worker.owner_id

    assert heartbeat_registry.is_alive(
        worker_id
    )

    worker.stop()

    assert not heartbeat_registry.is_alive(
        worker_id
    )

    assert not worker._lifecycle_heartbeat_thread.is_alive()

def test_worker_heartbeat_and_state_updates_are_concurrency_safe():
    registry = WorkerHeartbeatRegistry(
        key_prefix=f"test-concurrency-workers-{uuid4()}",
        heartbeat_ttl_seconds=5,
    )

    worker_id = "worker-concurrency"

    registry.register(
        worker_id=worker_id,
        metadata={
            "initial": True,
        },
    )

    errors: list[Exception] = []

    def send_heartbeats():
        try:
            for _ in range(50):
                assert registry.heartbeat(
                    worker_id,
                    metadata={
                        "source": "heartbeat",
                    },
                ) is True
        except Exception as exc:
            errors.append(exc)

    def update_state():
        try:
            for _ in range(50):
                assert registry.set_state(
                    worker_id,
                    "running",
                    metadata={
                        "source": "state",
                    },
                ) is True
        except Exception as exc:
            errors.append(exc)

    heartbeat_thread = threading.Thread(
        target=send_heartbeats
    )

    state_thread = threading.Thread(
        target=update_state
    )

    heartbeat_thread.start()
    state_thread.start()

    heartbeat_thread.join()
    state_thread.join()

    assert errors == []

    record = registry.get(worker_id)

    assert record is not None
    assert record["worker_id"] == worker_id
    assert record["status"] == "alive"
    assert record["state"] == "running"
    assert record["metadata"] in (
        {"source": "heartbeat"},
        {"source": "state"},
    )
    assert isinstance(
        record["last_heartbeat"],
        float,
    )

    registry.unregister(worker_id)