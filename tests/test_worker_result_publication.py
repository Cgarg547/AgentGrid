import pytest

from app.core.redis import redis_client
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue
from app.workers.worker import Worker

@pytest.fixture(autouse=True)
def clean_worker_result_publication_state():
    redis_client.delete(
        "agentgrid-test-worker-result-publication",
        "agentgrid-test-worker-results",
    )

    keys = redis_client.scan_iter(
        match="agentgrid:test:worker-result-publication:*"
    )

    for key in keys:
        redis_client.delete(key)

    yield

    redis_client.delete(
        "agentgrid-test-worker-result-publication",
        "agentgrid-test-worker-results",
    )

    keys = redis_client.scan_iter(
        match="agentgrid:test:worker-result-publication:*"
    )

    for key in keys:
        redis_client.delete(key)

def test_worker_publishes_completed_result():
    queue = TaskQueue(
        "agentgrid-test-worker-result-publication"
    )

    result_queue = TaskResultQueue(
        "agentgrid-test-worker-results"
    )

    def research_handler(*, step_name, inputs):
        return {
            "answer": inputs["input"],
        }

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": research_handler,
        },
        idempotency_store=IdempotencyStore(
            key_prefix="agentgrid:test:worker-result-publication"
        ),
        result_queue=result_queue,
    )

    queue.enqueue(
        {
            "task_id": "publication-task-123",
            "execution_id": "publication-execution-123",
            "step_name": "research",
            "agent_name": "research-agent",
            "inputs": {
                "input": "distributed execution",
            },
        }
    )

    result = worker.process_one()

    assert result is not None
    assert result["status"] == "completed"

    published_result = result_queue.consume()

    assert published_result == result