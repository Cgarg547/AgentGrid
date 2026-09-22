from uuid import uuid4
from app.workers.dead_letter import DeadLetterQueue
from app.workers.heartbeat import WorkerHeartbeatRegistry
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.worker import Worker


def create_worker():
    prefix = f"test-agentgrid-worker-state-{uuid4()}"

    registry = WorkerHeartbeatRegistry(
        key_prefix=f"{prefix}:workers",
        heartbeat_ttl_seconds=10,
    )

    worker = Worker(
        queue=TaskQueue(
            queue_name=f"{prefix}:queue"
        ),
        agent_handlers={
            "test-agent": lambda **kwargs: {
                "message": "success"
            }
        },
        idempotency_store=IdempotencyStore(
            key_prefix=f"{prefix}:idempotency"
        ),
        heartbeat_registry=registry,
    )

    return worker, registry


def test_worker_starts_in_idle_state():
    worker, registry = create_worker()

    record = registry.get(worker.owner_id)

    assert record is not None
    assert record["state"] == "idle"


def test_worker_becomes_idle_after_processing_task():
    worker, registry = create_worker()

    worker.queue.enqueue(
        {
            "task_id": f"task-{uuid4()}",
            "step_name": "test-step",
            "agent_name": "test-agent",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == "completed"

    record = registry.get(worker.owner_id)

    assert record is not None
    assert record["state"] == "idle"


def test_worker_is_running_while_task_executes():
    import threading
    import time

    worker, registry = create_worker()

    task_started = threading.Event()
    release_task = threading.Event()

    def slow_handler(**kwargs):
        task_started.set()
        release_task.wait(timeout=5)

        return {
            "message": "success"
        }

    worker.agent_handlers["test-agent"] = slow_handler

    worker.queue.enqueue(
        {
            "task_id": f"task-{uuid4()}",
            "step_name": "test-step",
            "agent_name": "test-agent",
            "inputs": {},
        }
    )

    result_holder = {}

    def run_worker():
        result_holder["result"] = worker.process_one()

    worker_thread = threading.Thread(
        target=run_worker
    )

    worker_thread.start()

    assert task_started.wait(timeout=2)

    record = registry.get(worker.owner_id)

    assert record is not None
    assert record["state"] == "running"
    assert record["metadata"]["step_name"] == "test-step"

    release_task.set()

    worker_thread.join(timeout=5)

    assert result_holder["result"] is not None
    assert result_holder["result"]["status"] == "completed"

    record = registry.get(worker.owner_id)

    assert record is not None
    assert record["state"] == "idle"


def test_worker_can_unregister_itself():
    worker, registry = create_worker()

    assert registry.is_alive(
        worker.owner_id
    ) is True

    worker.stop()

    assert registry.is_alive(
        worker.owner_id
    ) is False

def test_worker_becomes_idle_after_unknown_agent():
    heartbeat_registry = WorkerHeartbeatRegistry(
        key_prefix="test:unknown:agent:workers"
    )

    worker = Worker(
        queue=TaskQueue(
            "test:unknown:agent:queue:v2"
        ),
        agent_handlers={},
        heartbeat_registry=heartbeat_registry,
        dead_letter_queue=DeadLetterQueue(
            "test:unknown:agent:dead-letter:v2"
        ),
        idempotency_store=IdempotencyStore(
        key_prefix="test:unknown:agent:idempotency:v2"
        ),
    )

    worker.queue.enqueue({
        "task_id": "unknown-agent-task",
        "step_name": "unknown-step",
        "agent_name": "missing-agent",
    })

    try:
        result = worker.process_one()

        assert result is not None
        assert result["status"] == "dead_lettered"

        worker_state = heartbeat_registry.get(
            worker.owner_id
        )

        assert worker_state is not None
        assert worker_state["state"] == "idle"
    finally:
        worker.stop()