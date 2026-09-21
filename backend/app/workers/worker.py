from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
import time
from typing import Any, Callable
from app.workers.result_queue import TaskResultQueue
from app.workers.dead_letter import DeadLetterQueue
from app.workers.events import WorkerEvent
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
        dead_letter_queue: DeadLetterQueue | None = None,
        event_repository: Any | None = None,
        result_queue: TaskResultQueue | None = None,
    ):
        self.queue = queue
        self.agent_handlers = agent_handlers
        self.retry_policy = retry_policy or RetryPolicy()
        self.timeout_policy = timeout_policy or TimeoutPolicy()
        self.idempotency_store = (
            idempotency_store or IdempotencyStore()
        )
        self.dead_letter_queue = (
            dead_letter_queue or DeadLetterQueue()
        )
        self.event_repository = event_repository
        self.result_queue = result_queue
        self.events: list[WorkerEvent] = []

    def process_one(self) -> dict[str, Any] | None:
        task = self.queue.dequeue()

        if task is None:
            return None

        task_id = task["task_id"]
        step_name = task["step_name"]
        agent_name = task["agent_name"]
        execution_id = task.get("execution_id")

        self._record_event(
            "task_received",
            task_id,
            {
                "step_name": step_name,
                "agent_name": agent_name,
            },
        )

        existing = self.idempotency_store.get(task_id)

        if existing is not None:
            if existing["status"] == IdempotencyStore.COMPLETED_STATUS:
                return existing["result"]

            return {
                "task_id": task_id,
                "step_name": step_name,
                "agent_name": agent_name,
                "status": TaskStatus.FAILED.value,
                "attempt": 1,
                "error": "Task is already being processed.",
            }

        if not self.idempotency_store.claim(task_id):
            return {
                "task_id": task_id,
                "step_name": step_name,
                "agent_name": agent_name,
                "status": TaskStatus.FAILED.value,
                "attempt": 1,
                "error": "Task is already being processed.",
            }

        self._record_event(
            "task_claimed",
            task_id,
            {
                "step_name": step_name,
                "agent_name": agent_name,
            },
        )

        handler = self.agent_handlers.get(agent_name)

        if handler is None:
            result = {
                "task_id": task_id,
                "step_name": step_name,
                "agent_name": agent_name,
                "status": TaskStatus.DEAD_LETTERED.value,
                "attempt": 1,
                "error": (
                    f"No handler registered for agent "
                    f"'{agent_name}'."
                ),
            }

            self._record_event(
                "task_dead_lettered",
                task_id,
                {
                    "step_name": step_name,
                    "agent_name": agent_name,
                    "attempt": 1,
                    "reason": "unknown_agent",
                },
            )

            self.dead_letter_queue.enqueue(result)

            return result

        attempt = 0

        while True:
            attempt += 1

            self._record_event(
                "task_started",
                task_id,
                {
                    "step_name": step_name,
                    "agent_name": agent_name,
                    "attempt": attempt,
                },
            )

            heartbeat_stop = threading.Event()

            heartbeat_thread = threading.Thread(
                target=self._heartbeat,
                args=(task_id, heartbeat_stop),
                daemon=True,
            )

            heartbeat_thread.start()

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        handler,
                        step_name=step_name,
                        inputs=task.get("inputs", {}),
                    )

                    result = future.result(
                        timeout=self.timeout_policy.get_timeout()
                    )

                result_payload = {
                    "task_id": task_id,
                    "execution_id": execution_id,
                    "step_name": step_name,
                    "agent_name": agent_name,
                    "status": TaskStatus.COMPLETED.value,
                    "attempt": attempt,
                    "result": result,
                }

                self.idempotency_store.set(
                    task_id,
                    result_payload,
                )

                if self.result_queue is not None:
                    self.result_queue.publish(result_payload)

                self._record_event(
                    "task_completed",
                    task_id,
                    {
                        "step_name": step_name,
                        "agent_name": agent_name,
                        "attempt": attempt,
                    },
                )

                return result_payload

            except TimeoutError:
                result_payload = {
                    "task_id": task_id,
                    "step_name": step_name,
                    "agent_name": agent_name,
                    "status": TaskStatus.DEAD_LETTERED.value,
                    "attempt": attempt,
                    "error": (
                        f"Task exceeded timeout of "
                        f"{self.timeout_policy.get_timeout()} seconds."
                    ),
                }

                self._record_event(
                    "task_timed_out",
                    task_id,
                    {
                        "step_name": step_name,
                        "agent_name": agent_name,
                        "attempt": attempt,
                        "timeout_seconds": (
                            self.timeout_policy.get_timeout()
                        ),
                    },
                )

                self._record_event(
                    "task_dead_lettered",
                    task_id,
                    {
                        "step_name": step_name,
                        "agent_name": agent_name,
                        "attempt": attempt,
                        "reason": "timeout",
                    },
                )

                self.dead_letter_queue.enqueue(result_payload)

                return result_payload

            except Exception as exc:
                if not self.retry_policy.should_retry(attempt):
                    result_payload = {
                        "task_id": task_id,
                        "step_name": step_name,
                        "agent_name": agent_name,
                        "status": TaskStatus.DEAD_LETTERED.value,
                        "attempt": attempt,
                        "error": str(exc),
                    }

                    self._record_event(
                        "task_dead_lettered",
                        task_id,
                        {
                            "step_name": step_name,
                            "agent_name": agent_name,
                            "attempt": attempt,
                            "reason": "max_attempts_exceeded",
                            "error": str(exc),
                        },
                    )

                    self.dead_letter_queue.enqueue(result_payload)

                    return result_payload

                next_attempt = attempt + 1
                delay = self.retry_policy.get_delay(attempt)

                self._record_event(
                    "task_retrying",
                    task_id,
                    {
                        "step_name": step_name,
                        "agent_name": agent_name,
                        "attempt": attempt,
                        "next_attempt": next_attempt,
                        "delay_seconds": delay,
                        "error": str(exc),
                    },
                )

                time.sleep(delay)

            finally:
                heartbeat_stop.set()
                heartbeat_thread.join(timeout=1)

    def _record_event(
        self,
        event_type: str,
        task_id: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        event = WorkerEvent.create(
            event_type=event_type,
            task_id=task_id,
            data=data,
        )

        self.events.append(event)

        if self.event_repository is not None:
            self.event_repository.save(event)

    def _heartbeat(
        self,
        task_id: str,
        stop_event: threading.Event,
    ) -> None:
        interval = max(
            self.idempotency_store.claim_ttl_seconds / 3,
            0.1,
        )

        while not stop_event.wait(interval):
            renewed = self.idempotency_store.renew_claim(task_id)

            if not renewed:
                return