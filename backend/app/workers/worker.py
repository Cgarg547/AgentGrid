from concurrent.futures import ThreadPoolExecutor, TimeoutError
import time
from typing import Any, Callable

from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.retry import RetryPolicy
from app.workers.task_status import TaskStatus
from app.workers.timeout import TimeoutPolicy


class Worker:
    def __init__(
        self,
        queue: TaskQueue,
        agent_handlers: dict[str, Callable[..., Any]],
        retry_policy: RetryPolicy | None = None,
        timeout_policy: TimeoutPolicy | None = None,
        idempotency_store: IdempotencyStore | None = None,
    ):
        self.queue = queue
        self.agent_handlers = agent_handlers
        self.retry_policy = retry_policy or RetryPolicy()
        self.timeout_policy = timeout_policy or TimeoutPolicy()
        self.idempotency_store = (
            idempotency_store or IdempotencyStore()
        )

    def process_one(self) -> dict[str, Any] | None:
        task = self.queue.dequeue()

        if task is None:
            return None

        task_id = task["task_id"]

        existing = self.idempotency_store.get(task_id)

        if existing is not None:
            if existing["status"] == IdempotencyStore.COMPLETED_STATUS:
                return existing["result"]

            return {
                "task_id": task_id,
                "step_name": task["step_name"],
                "agent_name": task["agent_name"],
                "status": TaskStatus.FAILED.value,
                "attempt": 1,
                "error": "Task is already being processed.",
            }

        if not self.idempotency_store.claim(task_id):
            return {
                "task_id": task_id,
                "step_name": task["step_name"],
                "agent_name": task["agent_name"],
                "status": TaskStatus.FAILED.value,
                "attempt": 1,
                "error": "Task is already being processed.",
            }

        agent_name = task["agent_name"]
        handler = self.agent_handlers.get(agent_name)

        if handler is None:
            return {
                "task_id": task_id,
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
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        handler,
                        step_name=task["step_name"],
                        inputs=task.get("inputs", {}),
                    )

                    result = future.result(
                        timeout=self.timeout_policy.get_timeout()
                    )

                result_payload = {
                    "task_id": task_id,
                    "step_name": task["step_name"],
                    "agent_name": agent_name,
                    "status": TaskStatus.COMPLETED.value,
                    "attempt": attempt,
                    "result": result,
                }

                self.idempotency_store.set(
                    task_id,
                    result_payload,
                )

                return result_payload

            except TimeoutError:
                return {
                    "task_id": task_id,
                    "step_name": task["step_name"],
                    "agent_name": agent_name,
                    "status": TaskStatus.FAILED.value,
                    "attempt": attempt,
                    "error": (
                        f"Task exceeded timeout of "
                        f"{self.timeout_policy.get_timeout()} seconds."
                    ),
                }

            except Exception as exc:
                if not self.retry_policy.should_retry(attempt):
                    return {
                        "task_id": task_id,
                        "step_name": task["step_name"],
                        "agent_name": agent_name,
                        "status": TaskStatus.FAILED.value,
                        "attempt": attempt,
                        "error": str(exc),
                    }

                time.sleep(
                    self.retry_policy.get_delay(attempt)
                )