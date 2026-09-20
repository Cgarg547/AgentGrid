from uuid import uuid4
import time
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.retry import RetryPolicy
from app.workers.worker import Worker
from app.workers.worker_pool import WorkerPool


def test_worker_pool_processes_tasks_concurrently():
    queue = TaskQueue(
        f"test-agentgrid-worker-pool-{uuid4()}"
    )

    idempotency_store = IdempotencyStore(
        key_prefix=f"test-agentgrid-pool-idempotency-{uuid4()}"
    )

    executions = []

    def handler(**kwargs):
        executions.append(kwargs["step_name"])
        return {
            "step": kwargs["step_name"],
        }

    workers = [
        Worker(
            queue=queue,
            agent_handlers={
                "research-agent": handler,
            },
            retry_policy=RetryPolicy(
                max_attempts=1,
                base_delay=0,
            ),
            idempotency_store=idempotency_store,
        )
        for _ in range(3)
    ]

    for index in range(3):
        queue.enqueue(
            {
                "task_id": f"pool-task-{uuid4()}",
                "agent_name": "research-agent",
                "step_name": f"step-{index}",
                "inputs": {},
            }
        )

    pool = WorkerPool(workers)

    results = []

    for _ in range(3):
        results.extend(pool.process_available_tasks())

    assert len(results) == 3
    assert len(executions) == 3
    assert queue.size() == 0


def test_worker_pool_requires_at_least_one_worker():
    try:
        WorkerPool([])
    except ValueError as exc:
        assert str(exc) == (
            "Worker pool must contain at least one worker."
        )
    else:
        raise AssertionError(
            "WorkerPool should reject an empty worker list."
        )

def test_worker_pool_runs_workers_concurrently():
    queue = TaskQueue(
        f"test-agentgrid-worker-pool-timing-{uuid4()}"
    )

    idempotency_store = IdempotencyStore(
        key_prefix=f"test-agentgrid-pool-timing-{uuid4()}"
    )

    def slow_handler(**kwargs):
        time.sleep(0.2)
        return {
            "step": kwargs["step_name"],
        }

    workers = [
        Worker(
            queue=queue,
            agent_handlers={
                "research-agent": slow_handler,
            },
            retry_policy=RetryPolicy(
                max_attempts=1,
                base_delay=0,
            ),
            idempotency_store=idempotency_store,
        )
        for _ in range(2)
    ]

    for index in range(2):
        queue.enqueue(
            {
                "task_id": f"timing-task-{uuid4()}",
                "agent_name": "research-agent",
                "step_name": f"step-{index}",
                "inputs": {},
            }
        )

    pool = WorkerPool(workers)

    start = time.perf_counter()

    results = pool.process_available_tasks()

    elapsed = time.perf_counter() - start

    assert len(results) == 2
    assert queue.size() == 0

    assert elapsed < 0.35

def test_worker_pool_start_and_stop_processes_queued_task():
    queue = TaskQueue(
        f"test-agentgrid-worker-pool-lifecycle-{uuid4()}"
    )

    idempotency_store = IdempotencyStore(
        key_prefix=f"test-agentgrid-pool-lifecycle-{uuid4()}"
    )

    executions = []

    def handler(**kwargs):
        executions.append(kwargs["step_name"])
        return {
            "step": kwargs["step_name"],
        }

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": handler,
        },
        retry_policy=RetryPolicy(
            max_attempts=1,
            base_delay=0,
        ),
        idempotency_store=idempotency_store,
    )

    queue.enqueue(
        {
            "task_id": f"lifecycle-task-{uuid4()}",
            "agent_name": "research-agent",
            "step_name": "research",
            "inputs": {},
        }
    )

    pool = WorkerPool(
        [worker],
        poll_interval=0.05,
    )

    pool.start()

    deadline = time.time() + 2

    while not executions and time.time() < deadline:
        time.sleep(0.05)

    pool.stop()

    assert executions == ["research"]
    assert queue.size() == 0

def test_worker_pool_start_is_idempotent():
    queue = TaskQueue(
        f"test-agentgrid-worker-pool-start-{uuid4()}"
    )

    worker = Worker(
        queue=queue,
        agent_handlers={
            "research-agent": lambda **kwargs: {
                "result": "success"
            },
        },
        retry_policy=RetryPolicy(
            max_attempts=1,
            base_delay=0,
        ),
        idempotency_store=IdempotencyStore(
            key_prefix=f"test-agentgrid-pool-start-{uuid4()}"
        ),
    )

    pool = WorkerPool(
        [worker],
        poll_interval=0.05,
    )

    pool.start()

    first_thread_count = len(pool._threads)

    pool.start()

    second_thread_count = len(pool._threads)

    pool.stop()

    assert first_thread_count == 1
    assert second_thread_count == 1
    assert pool._threads == []