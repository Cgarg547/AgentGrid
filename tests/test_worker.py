import time
from uuid import uuid4

from app.workers.dead_letter import DeadLetterQueue
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.retry import RetryPolicy
from app.workers.task_status import TaskStatus
from app.workers.timeout import TimeoutPolicy
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
            "task_id": f"task-1-{uuid4()}",
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
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

    task_id = f"task-unknown-{uuid4()}"

    worker = Worker(
        queue=queue,
        agent_handlers={},
    )

    queue.enqueue(
        {
            "task_id": task_id,
            "agent_name": "unknown-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["task_id"] == task_id
    assert result["status"] == TaskStatus.DEAD_LETTERED.value
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
            base_delay=0,
        ),
    )

    queue.enqueue(
        {
            "task_id": f"task-retry-{uuid4()}",
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
            "task_id": f"task-permanent-failure-{uuid4()}",
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.DEAD_LETTERED.value
    assert result["attempt"] == 3
    assert result["error"] == "Permanent failure."
    assert attempts["count"] == 3


def test_worker_fails_when_task_times_out():
    queue = TaskQueue(
        f"test-agentgrid-worker-timeout-{uuid4()}"
    )

    def slow_handler(**kwargs):
        time.sleep(0.2)
        return {"result": "too slow"}

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": slow_handler,
        },
        retry_policy=RetryPolicy(
            max_attempts=1,
            base_delay=0,
        ),
        timeout_policy=TimeoutPolicy(
            timeout_seconds=0.05,
        ),
    )

    queue.enqueue(
        {
            "task_id": f"task-timeout-{uuid4()}",
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.DEAD_LETTERED.value
    assert result["attempt"] == 1
    assert result["error"] == (
        "Task exceeded timeout of 0.05 seconds."
    )


def test_worker_returns_stored_result_for_completed_duplicate_task():
    queue = TaskQueue(
        f"test-agentgrid-worker-idempotency-{uuid4()}"
    )

    executions = {"count": 0}

    def handler(**kwargs):
        executions["count"] += 1
        return {"value": "success"}

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": handler,
        },
        retry_policy=RetryPolicy(
            max_attempts=1,
            base_delay=0,
        ),
        timeout_policy=TimeoutPolicy(
            timeout_seconds=1,
        ),
        idempotency_store=IdempotencyStore(
            key_prefix=f"test-agentgrid-idempotency-{uuid4()}"
        ),
    )

    task = {
        "task_id": "task-duplicate",
        "agent_name": "research-agent",
        "step_name": "research",
        "inputs": {},
    }

    queue.enqueue(task)
    first_result = worker.process_one()

    queue.enqueue(task)
    second_result = worker.process_one()

    assert first_result is not None
    assert second_result is not None
    assert first_result == second_result
    assert executions["count"] == 1


def test_worker_rejects_task_already_claimed_by_another_worker():
    queue = TaskQueue(
        f"test-agentgrid-worker-claimed-{uuid4()}"
    )

    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}"
    )

    task_id = "task-already-claimed"

    assert store.claim(task_id) is True

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": lambda **kwargs: {
                "value": "should not execute"
            },
        },
        retry_policy=RetryPolicy(
            max_attempts=1,
            base_delay=0,
        ),
        timeout_policy=TimeoutPolicy(
            timeout_seconds=1,
        ),
        idempotency_store=store,
    )

    queue.enqueue(
        {
            "task_id": task_id,
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["task_id"] == task_id
    assert result["status"] == TaskStatus.FAILED.value
    assert result["attempt"] == 1
    assert result["error"] == "Task is already being processed."


def test_worker_sends_permanent_failure_to_dead_letter_queue():
    queue = TaskQueue(
        f"test-agentgrid-worker-dlq-{uuid4()}"
    )

    dead_letter_queue = DeadLetterQueue(
        f"test-agentgrid-dlq-{uuid4()}"
    )

    def failing_handler(**kwargs):
        raise RuntimeError("Permanent failure.")

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": failing_handler,
        },
        retry_policy=RetryPolicy(
            max_attempts=2,
            base_delay=0,
        ),
        dead_letter_queue=dead_letter_queue,
    )

    task = {
        "task_id": f"task-dlq-{uuid4()}",
        "agent_name": "research-agent",
        "step_name": "research",
        "inputs": {},
    }

    queue.enqueue(task)

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.DEAD_LETTERED.value
    assert result["attempt"] == 2
    assert result["error"] == "Permanent failure."

    dead_lettered_task = dead_letter_queue.dequeue()

    assert dead_lettered_task == result
    assert dead_letter_queue.size() == 0


def test_worker_sends_timeout_to_dead_letter_queue():
    queue = TaskQueue(
        f"test-agentgrid-worker-timeout-dlq-{uuid4()}"
    )

    dead_letter_queue = DeadLetterQueue(
        f"test-agentgrid-timeout-dlq-{uuid4()}"
    )

    def slow_handler(**kwargs):
        time.sleep(0.2)
        return {"result": "too slow"}

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": slow_handler,
        },
        retry_policy=RetryPolicy(
            max_attempts=1,
            base_delay=0,
        ),
        timeout_policy=TimeoutPolicy(
            timeout_seconds=0.05,
        ),
        dead_letter_queue=dead_letter_queue,
    )

    task = {
        "task_id": f"task-timeout-dlq-{uuid4()}",
        "agent_name": "research-agent",
        "step_name": "research",
        "inputs": {},
    }

    queue.enqueue(task)

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.DEAD_LETTERED.value
    assert result["attempt"] == 1
    assert result["error"] == (
        "Task exceeded timeout of 0.05 seconds."
    )

    dead_lettered_task = dead_letter_queue.dequeue()

    assert dead_lettered_task == result
    assert dead_letter_queue.size() == 0

def test_worker_uses_unique_lease_owner():
    queue = TaskQueue(
        f"test-agentgrid-worker-owner-{uuid4()}"
    )

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": lambda **kwargs: {
                "value": "success"
            },
        },
    )

    assert worker.owner_id
    assert isinstance(worker.owner_id, str)

    second_worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": lambda **kwargs: {
                "value": "success"
            },
        },
    )

    assert second_worker.owner_id
    assert worker.owner_id != second_worker.owner_id

def test_worker_can_reclaim_task_after_previous_lease_expires():
    queue = TaskQueue(
        f"test-agentgrid-worker-reclaim-{uuid4()}"
    )

    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}",
        claim_ttl_seconds=1,
    )

    task_id = f"task-reclaim-{uuid4()}"

    first_worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": lambda **kwargs: {
                "worker": "first"
            },
        },
        idempotency_store=store,
    )

    second_worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": lambda **kwargs: {
                "worker": "second"
            },
        },
        idempotency_store=store,
    )

    assert store.claim(
        task_id,
        owner_id=first_worker.owner_id,
    ) is True

    time.sleep(1.1)

    queue.enqueue(
        {
            "task_id": task_id,
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    result = second_worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.COMPLETED.value
    assert result["result"] == {
        "worker": "second"
    }