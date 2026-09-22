from app.workers.dead_letter import DeadLetterQueue
from app.workers.heartbeat import WorkerHeartbeatRegistry
from app.workers.metrics import WorkerMetrics
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue


def test_queue_metrics_report_queue_sizes():
    task_queue = TaskQueue(
        "test:metrics:tasks"
    )
    result_queue = TaskResultQueue(
        "test:metrics:results"
    )
    dead_letter_queue = DeadLetterQueue(
        "test:metrics:dead-letter"
    )

    task_queue.enqueue({
        "task_id": "task-1",
    })

    result_queue.publish({
        "task_id": "task-1",
        "status": "completed",
    })

    dead_letter_queue.enqueue({
        "task_id": "task-2",
    })

    metrics = WorkerMetrics(
        task_queue=task_queue,
        result_queue=result_queue,
        dead_letter_queue=dead_letter_queue,
        heartbeat_registry=WorkerHeartbeatRegistry(
            key_prefix="test:metrics:workers"
        ),
    )

    result = metrics.queue_metrics()

    assert result == {
        "tasks": 1,
        "results": 1,
        "dead_letter": 1,
    }

    task_queue.dequeue()
    result_queue.consume()
    dead_letter_queue.dequeue()


def test_worker_metrics_report_worker_states():
    heartbeat_registry = WorkerHeartbeatRegistry(
        key_prefix="test:metrics:workers"
    )

    worker_1 = heartbeat_registry.register(
        worker_id="worker-1"
    )

    worker_2 = heartbeat_registry.register(
        worker_id="worker-2"
    )

    heartbeat_registry.set_state(
        worker_2,
        "running",
    )

    metrics = WorkerMetrics(
        task_queue=TaskQueue(
            "test:metrics:tasks:workers"
        ),
        result_queue=TaskResultQueue(
            "test:metrics:results:workers"
        ),
        dead_letter_queue=DeadLetterQueue(
            "test:metrics:dead-letter:workers"
        ),
        heartbeat_registry=heartbeat_registry,
    )

    result = metrics.worker_metrics()

    assert result == {
        "total": 2,
        "idle": 1,
        "running": 1,
        "utilization": 0.5,
    }

    heartbeat_registry.unregister(worker_1)
    
    heartbeat_registry.unregister(worker_2)

def test_metrics_snapshot_combines_queue_and_worker_metrics():
    task_queue = TaskQueue(
        "test:metrics:snapshot:tasks"
    )
    result_queue = TaskResultQueue(
        "test:metrics:snapshot:results"
    )
    dead_letter_queue = DeadLetterQueue(
        "test:metrics:snapshot:dead-letter"
    )
    heartbeat_registry = WorkerHeartbeatRegistry(
        key_prefix="test:metrics:snapshot:workers"
    )

    worker_id = heartbeat_registry.register(
        worker_id="snapshot-worker"
    )

    task_queue.enqueue({
        "task_id": "task-1",
    })

    task_queue.enqueue({
        "task_id": "task-2",
    })

    result_queue.publish({
        "task_id": "task-3",
        "status": "completed",
    })

    metrics = WorkerMetrics(
        task_queue=task_queue,
        result_queue=result_queue,
        dead_letter_queue=dead_letter_queue,
        heartbeat_registry=heartbeat_registry,
    )

    result = metrics.snapshot()

    assert result == {
        "queues": {
            "tasks": 2,
            "results": 1,
            "dead_letter": 0,
        },
        "workers": {
            "total": 1,
            "idle": 1,
            "running": 0,
            "utilization": 0.0,
        },
    }

    task_queue.dequeue()
    task_queue.dequeue()
    result_queue.consume()
    heartbeat_registry.unregister(worker_id)