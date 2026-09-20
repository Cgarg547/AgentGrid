from uuid import uuid4

from app.workers.dead_letter import DeadLetterQueue


def test_dead_letter_queue_enqueue_and_dequeue():
    queue = DeadLetterQueue(
        f"test-agentgrid-dead-letter-{uuid4()}"
    )

    task = {
        "task_id": "task-failed",
        "agent_name": "research-agent",
        "step_name": "research",
        "status": "failed",
        "attempt": 3,
        "error": "Permanent failure.",
    }

    queue.enqueue(task)

    assert queue.size() == 1
    assert queue.dequeue() == task
    assert queue.size() == 0


def test_dead_letter_queue_returns_none_when_empty():
    queue = DeadLetterQueue(
        f"test-agentgrid-dead-letter-{uuid4()}"
    )

    assert queue.dequeue() is None


def test_dead_letter_queue_clear():
    queue = DeadLetterQueue(
        f"test-agentgrid-dead-letter-{uuid4()}"
    )

    queue.enqueue({
        "task_id": "task-1",
        "status": "failed",
    })

    queue.enqueue({
        "task_id": "task-2",
        "status": "failed",
    })

    assert queue.size() == 2

    queue.clear()

    assert queue.size() == 0