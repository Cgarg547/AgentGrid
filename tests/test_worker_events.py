import time
import uuid

from app.workers.dead_letter import DeadLetterQueue
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.retry import RetryPolicy
from app.workers.task_status import TaskStatus
from app.workers.timeout import TimeoutPolicy
from app.workers.worker import Worker


def unique_task_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def test_worker_records_successful_task_lifecycle():
    task_id = unique_task_id("event-success")

    worker = Worker(
        queue=TaskQueue("test-worker-event-success"),
        agent_handlers={
            "researcher": lambda **kwargs: {
                "message": "completed"
            }
        },
    )

    worker.queue.enqueue(
        {
            "task_id": task_id,
            "step_name": "research",
            "agent_name": "researcher",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.COMPLETED.value

    event_types = [
        event.event_type
        for event in worker.events
    ]

    assert event_types == [
        "task_received",
        "task_claimed",
        "task_started",
        "task_completed",
    ]


def test_worker_records_retry_lifecycle():
    task_id = unique_task_id("event-retry")
    attempts = {"count": 0}

    def failing_handler(**kwargs):
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise RuntimeError("temporary failure")

        return {
            "message": "recovered"
        }

    worker = Worker(
        queue=TaskQueue("test-worker-event-retry"),
        agent_handlers={
            "researcher": failing_handler
        },
        retry_policy=RetryPolicy(
            max_attempts=2,
            base_delay=0.01,
        ),
    )

    worker.queue.enqueue(
        {
            "task_id": task_id,
            "step_name": "research",
            "agent_name": "researcher",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.COMPLETED.value
    assert attempts["count"] == 2

    event_types = [
        event.event_type
        for event in worker.events
    ]

    assert event_types == [
        "task_received",
        "task_claimed",
        "task_started",
        "task_retrying",
        "task_started",
        "task_completed",
    ]


def test_worker_records_timeout_and_dead_letter_events():
    task_id = unique_task_id("event-timeout")

    def slow_handler(**kwargs):
        time.sleep(0.05)

        return {
            "message": "too late"
        }

    worker = Worker(
        queue=TaskQueue("test-worker-event-timeout"),
        agent_handlers={
            "researcher": slow_handler
        },
        timeout_policy=TimeoutPolicy(
            timeout_seconds=0.01
        ),
        dead_letter_queue=DeadLetterQueue(
            "test-worker-event-timeout-dlq"
        ),
    )

    worker.queue.enqueue(
        {
            "task_id": task_id,
            "step_name": "research",
            "agent_name": "researcher",
            "inputs": {},
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == TaskStatus.DEAD_LETTERED.value

    event_types = [
        event.event_type
        for event in worker.events
    ]

    assert event_types == [
        "task_received",
        "task_claimed",
        "task_started",
        "task_timed_out",
        "task_dead_lettered",
    ]