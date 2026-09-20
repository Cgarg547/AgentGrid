from uuid import uuid4

from app.workers.queue import TaskQueue


def test_task_queue_enqueue_and_dequeue():
    queue_name = f"test-agentgrid-{uuid4()}"

    queue = TaskQueue(queue_name)

    task = {
        "task_id": "task-1",
        "agent_name": "research-agent",
        "step_name": "research",
    }

    assert queue.size() == 0

    queue.enqueue(task)

    assert queue.size() == 1

    result = queue.dequeue()

    assert result == task
    assert queue.size() == 0