from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.workflows.workflow import Workflow, WorkflowStep
from app.workflows.workflow_state import (
    StepStatus,
    WorkflowStatus,
)


@dataclass
class WorkflowExecution:
    workflow: Workflow
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    status: WorkflowStatus = WorkflowStatus.PENDING
    step_statuses: dict[str, StepStatus] = field(default_factory=dict)
    step_results: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for step in self.workflow.steps:
            self.step_statuses.setdefault(
                step.name,
                StepStatus.PENDING,
            )

    def mark_step_running(self, step_name: str) -> None:
        self._ensure_step_exists(step_name)
        self.step_statuses[step_name] = StepStatus.RUNNING
        self.status = WorkflowStatus.RUNNING

    def mark_step_completed(
        self,
        step_name: str,
        result: Any = None,
    ) -> None:
        self._ensure_step_exists(step_name)

        self.step_statuses[step_name] = StepStatus.COMPLETED
        self.step_results[step_name] = result

        if all(
            status == StepStatus.COMPLETED
            for status in self.step_statuses.values()
        ):
            self.status = WorkflowStatus.COMPLETED

    def mark_step_failed(self, step_name: str) -> None:
        self._ensure_step_exists(step_name)
        self.step_statuses[step_name] = StepStatus.FAILED
        self.status = WorkflowStatus.FAILED

    def get_completed_steps(self) -> set[str]:
        return {
            name
            for name, status in self.step_statuses.items()
            if status == StepStatus.COMPLETED
        }

    def get_ready_steps(self) -> list[WorkflowStep]:
        return self.workflow.get_ready_steps(
            self.get_completed_steps()
        )

    def get_step_result(self, step_name: str) -> Any:
        self._ensure_step_exists(step_name)

        if step_name not in self.step_results:
            raise KeyError(
                f"Step '{step_name}' has no result yet."
            )

        return self.step_results[step_name]

    def _ensure_step_exists(self, step_name: str) -> None:
        if step_name not in self.step_statuses:
            raise KeyError(
                f"Workflow step '{step_name}' does not exist."
            )