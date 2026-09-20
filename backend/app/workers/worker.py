from typing import Any, Callable

from app.workers.queue import TaskQueue
from app.workers.retry import RetryPolicy
from app.workers.task_status import TaskStatus


class Worker:
    def __init__(
        self,
        queue: TaskQueue,
        agent_handlers: dict[str, Callable[..., Any]],
        retry_policy: RetryPolicy | None = None,
    ):
        self.queue = queue
        self.agent_handlers = agent_handlers
        self.retry_policy = retry_policy or RetryPolicy()

    def process_one(self) -> dict[str, Any] | None:
        task = self.queue.dequeue()

        if task is None:
            return None

        agent_name = task["agent_name"]
        handler = self.agent_handlers.get(agent_name)

        if handler is None:
            return {
                "task_id": task["task_id"],
                "step_name": task["step_name"],
                "agent_name": agent_name,
                "status": TaskStatus.FAILED.value,
                "attempt": 1,
                "error": (
                    f"No handler registered for agent "
                    f"'{agent_name}'."
                ),
            }

        attempt = 0

        while True:
            attempt += 1

            try:
                result = handler(
                    step_name=task["step_name"],
                    inputs=task.get("inputs", {}),
                )

                return {
                    "task_id": task["task_id"],
                    "step_name": task["step_name"],
                    "agent_name": agent_name,
                    "status": TaskStatus.COMPLETED.value,
                    "attempt": attempt,
                    "result": result,
                }

            except Exception as exc:
                if not self.retry_policy.should_retry(attempt):
                    return {
                        "task_id": task["task_id"],
                        "step_name": task["step_name"],
                        "agent_name": agent_name,
                        "status": TaskStatus.FAILED.value,
                        "attempt": attempt,
                        "error": str(exc),
                    }