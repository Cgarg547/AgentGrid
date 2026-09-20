from uuid import uuid4

from app.workers.queue import TaskQueue
from app.workers.retry import RetryPolicy
from app.workers.task_status import TaskStatus
from app.workers.worker import Worker


def test_worker_processes_task():
    queue = TaskQueue(
        f"test-agentgrid-worker-{uuid4()}"
    )

    handlers = {
        "research-agent": lambda **kwargs: {
            "findings": [
                "AI orchestration",
                "distributed workers",
            ]
        }
    }

    worker = Worker(
        queue=queue,
        agent_handlers=handlers,
    )

    queue.enqueue(
        {
            "task_id": "task-1",
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["task_id"] == "task-1"
    assert result["step_name"] == "research"
    assert result["agent_name"] == "research-agent"
    assert result["status"] == TaskStatus.COMPLETED.value
    assert result["attempt"] == 1
    assert result["result"] == {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

    assert queue.size() == 0


def test_worker_rejects_unknown_agent():
    queue = TaskQueue(
        f"test-agentgrid-worker-{uuid4()}"
    )

    worker = Worker(
        queue=queue,
        agent_handlers={},
    )

    queue.enqueue(
        {
            "task_id": "task-unknown",
            "agent_name": "unknown-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["task_id"] == "task-unknown"
    assert result["status"] == TaskStatus.FAILED.value
    assert result["attempt"] == 1
    assert result["error"] == (
        "No handler registered for agent "
        "'unknown-agent'."
    )


def test_worker_retries_failed_agent():
    queue = TaskQueue(
        f"test-agentgrid-worker-{uuid4()}"
    )

    attempts = {"count": 0}

    def flaky_handler(**kwargs):
        attempts["count"] += 1

        if attempts["count"] < 3:
            raise RuntimeError("Temporary failure.")

        return {
            "result": "success"
        }

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": flaky_handler,
        },
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay=0
        ),
    )

    queue.enqueue(
        {
            "task_id": "task-retry",
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.COMPLETED.value
    assert result["attempt"] == 3
    assert result["result"] == {
        "result": "success"
    }
    assert attempts["count"] == 3


def test_worker_fails_after_max_attempts():
    queue = TaskQueue(
        f"test-agentgrid-worker-{uuid4()}"
    )

    attempts = {"count": 0}

    def failing_handler(**kwargs):
        attempts["count"] += 1
        raise RuntimeError("Permanent failure.")

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": failing_handler,
        },
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay=0,
        ),
    )

    queue.enqueue(
        {
            "task_id": "task-permanent-failure",
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.FAILED.value
    assert result["attempt"] == 3
    assert result["error"] == "Permanent failure."
    assert attempts["count"] == 3