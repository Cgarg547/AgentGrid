from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from app.workflows.execution import WorkflowExecution
from app.workflows.workflow import WorkflowStep


class WorkflowRunner:
    def __init__(
        self,
        execution: WorkflowExecution,
        agent_handlers: dict[str, Callable[..., Any]],
        max_workers: int = 4,
        on_state_change: Callable[
            [WorkflowExecution], None
        ] | None = None,
    ):
        self.execution = execution
        self.agent_handlers = agent_handlers
        self.max_workers = max_workers
        self.on_state_change = on_state_change

    def run(self) -> WorkflowExecution:
        self.execution.workflow.validate()

        while self.execution.status.value != "completed":
            ready_steps = self.execution.get_ready_steps()

            if not ready_steps:
                if self.execution.status.value == "failed":
                    return self.execution

                raise RuntimeError(
                    "Workflow cannot make progress. "
                    "There may be a dependency cycle or invalid state."
                )

            with ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = {
                    executor.submit(self._run_step, step): step
                    for step in ready_steps
                }

                for future in as_completed(futures):
                    future.result()

        return self.execution

    def _run_step(self, step: WorkflowStep) -> None:
        handler = self.agent_handlers.get(step.agent_name)

        if handler is None:
            self.execution.mark_step_failed(step.name)
            self._persist_state()

            raise KeyError(
                f"No handler registered for agent "
                f"'{step.agent_name}'."
            )

        self.execution.mark_step_running(step.name)
        self._persist_state()

        try:
            inputs = {
                dependency: self.execution.get_step_result(dependency)
                for dependency in step.depends_on
            }

            result = handler(
                step_name=step.name,
                inputs=inputs,
            )

            self.execution.mark_step_completed(
                step.name,
                result=result,
            )
            self._persist_state()

        except Exception:
            self.execution.mark_step_failed(step.name)
            self._persist_state()
            raise

    def _persist_state(self) -> None:
        if self.on_state_change is not None:
            self.on_state_change(self.execution)