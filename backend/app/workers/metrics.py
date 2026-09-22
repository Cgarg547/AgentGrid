from typing import Any

from app.workers.dead_letter import DeadLetterQueue
from app.workers.heartbeat import WorkerHeartbeatRegistry
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue


class WorkerMetrics:
    def __init__(
        self,
        task_queue: TaskQueue | None = None,
        result_queue: TaskResultQueue | None = None,
        dead_letter_queue: DeadLetterQueue | None = None,
        heartbeat_registry: WorkerHeartbeatRegistry | None = None,
    ):
        self.task_queue = task_queue or TaskQueue(
            "agentgrid:tasks"
        )
        self.result_queue = result_queue or TaskResultQueue(
            "agentgrid:results"
        )
        self.dead_letter_queue = (
            dead_letter_queue or DeadLetterQueue()
        )
        self.heartbeat_registry = (
            heartbeat_registry
            or WorkerHeartbeatRegistry()
        )

    def queue_metrics(self) -> dict[str, int]:
        return {
            "tasks": self.task_queue.size(),
            "results": self.result_queue.size(),
            "dead_letter": self.dead_letter_queue.size(),
        }

    def worker_metrics(self) -> dict[str, Any]:
        workers = self.heartbeat_registry.list_workers()

        total_workers = len(workers)

        idle_workers = sum(
            worker.get("state") == "idle"
            for worker in workers
        )

        running_workers = sum(
            worker.get("state") == "running"
            for worker in workers
        )

        utilization = (
            running_workers / total_workers
            if total_workers > 0
            else 0.0
        )

        return {
            "total": total_workers,
            "idle": idle_workers,
            "running": running_workers,
            "utilization": utilization,
        }
    
    def snapshot(self) -> dict[str, Any]:
        return {
            "queues": self.queue_metrics(),
            "workers": self.worker_metrics(),
        }