from typing import Any

from app.services.task_dispatcher import TaskDispatcher
from app.workers.result_queue import TaskResultQueue
from app.workflows.execution import WorkflowExecution


class WorkflowCoordinator:
    def __init__(
        self,
        dispatcher: TaskDispatcher,
        result_queue: TaskResultQueue,
    ):
        self.dispatcher = dispatcher
        self.result_queue = result_queue

    def dispatch_ready_steps(
        self,
        execution: WorkflowExecution,
        inputs: dict[str, Any] | None = None,
    ) -> list[str]:
        inputs = inputs or {}
        dispatched: list[str] = []

        for step in execution.get_ready_steps():
            step_inputs = {
                dependency: execution.get_step_result(dependency)
                for dependency in step.depends_on
            }

            if not step.depends_on:
                step_inputs.update(inputs)

            execution.mark_step_running(step.name)

            task_id = (
                f"{execution.execution_id}:{step.name}"
            )

            self.dispatcher.dispatch(
                task_id=task_id,
                execution_id=execution.execution_id,
                step_name=step.name,
                agent_name=step.agent_name,
                inputs=step_inputs,
            )

            dispatched.append(step.name)

        return dispatched

    def process_result(
        self,
        execution: WorkflowExecution,
        result: dict[str, Any],
    ) -> list[str]:
        if result["execution_id"] != execution.execution_id:
            raise ValueError(
                "Task result belongs to a different execution."
            )

        if result["status"] != "completed":
            execution.mark_step_failed(
                result["step_name"]
            )
            return []

        execution.mark_step_completed(
            result["step_name"],
            result=result["result"],
        )

        return self.dispatch_ready_steps(execution)