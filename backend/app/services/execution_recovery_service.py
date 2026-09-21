from typing import Any

from app.services.execution_checkpoint_repository import (
    ExecutionCheckpointRepository,
)
from app.services.postgres_execution_repository import (
    PostgresExecutionRepository,
)
from app.workflows.execution import WorkflowExecution
from app.workflows.workflow import Workflow
from app.workflows.workflow_state import (
    StepStatus,
    WorkflowStatus,
)


class ExecutionRecoveryService:
    def __init__(
        self,
        checkpoint_repository: (
            ExecutionCheckpointRepository | None
        ) = None,
        execution_repository: (
            PostgresExecutionRepository | None
        ) = None,
    ):
        self.checkpoint_repository = checkpoint_repository
        self.execution_repository = execution_repository

    def recover_latest_state(
        self,
        execution_id: str,
    ) -> dict[str, Any] | None:
        checkpoint = (
            self.checkpoint_repository.get_latest(
                execution_id
            )
        )

        if checkpoint is None:
            return None

        durable_state = (
            self.checkpoint_repository.deserialize_state(
                checkpoint.state
            )
        )

        return {
            "execution_id": checkpoint.execution_id,
            "step_name": checkpoint.step_name,
            "status": checkpoint.status,
            "step_statuses": durable_state[
                "step_statuses"
            ],
            "step_results": durable_state[
                "step_results"
            ],
        }

    def recover_execution(
        self,
        workflow: Workflow,
        execution_id: str,
    ) -> WorkflowExecution | None:
        checkpoint = (
            self.checkpoint_repository.get_latest(
                execution_id
            )
        )

        if checkpoint is None:
            return None

        durable_state = (
            self.checkpoint_repository.deserialize_state(
                checkpoint.state
            )
        )

        step_statuses = {
            step_name: StepStatus(status)
            for step_name, status
            in durable_state["step_statuses"].items()
        }

        step_results = durable_state[
            "step_results"
        ]

        workflow_status = self._get_workflow_status(
            step_statuses
        )

        return WorkflowExecution.from_checkpoint(
            workflow=workflow,
            execution_id=execution_id,
            status=workflow_status,
            step_statuses=step_statuses,
            step_results=step_results,
        )

    def recover_distributed_execution(
        self,
        workflow: Workflow,
        execution_id: str,
    ) -> WorkflowExecution | None:
        if self.execution_repository is None:
            return None

        record = self.execution_repository.get(
            execution_id
        )

        if record is None:
            return None

        if record.workflow_name != workflow.name:
            raise ValueError(
                "Execution belongs to a different workflow."
            )

        step_statuses = {
            step_name: StepStatus(status)
            for step_name, status
            in record.step_statuses.items()
        }

        step_results = record.step_results

        return WorkflowExecution.from_checkpoint(
            workflow=workflow,
            execution_id=record.execution_id,
            status=WorkflowStatus(record.status),
            step_statuses=step_statuses,
            step_results=step_results,
        )

    @staticmethod
    def _get_workflow_status(
        step_statuses: dict[str, StepStatus],
    ) -> WorkflowStatus:
        if any(
            status == StepStatus.FAILED
            for status in step_statuses.values()
        ):
            return WorkflowStatus.FAILED

        if all(
            status == StepStatus.COMPLETED
            for status in step_statuses.values()
        ):
            return WorkflowStatus.COMPLETED

        if any(
            status == StepStatus.RUNNING
            for status in step_statuses.values()
        ):
            return WorkflowStatus.RUNNING

        if any(
            status == StepStatus.COMPLETED
            for status in step_statuses.values()
        ):
            return WorkflowStatus.RUNNING

        return WorkflowStatus.PENDING