from typing import Any

from app.workers.queue import TaskQueue


class TaskDispatcher:
    def __init__(
        self,
        queue: TaskQueue,
    ):
        self.queue = queue

    def dispatch(
        self,
        task_id: str,
        execution_id: str,
        step_name: str,
        agent_name: str,
        inputs: dict[str, Any],
    ) -> None:
        task = {
            "task_id": task_id,
            "execution_id": execution_id,
            "step_name": step_name,
            "agent_name": agent_name,
            "inputs": inputs,
        }

        self.queue.enqueue(task)