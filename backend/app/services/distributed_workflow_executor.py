from typing import Any

from app.services.postgres_execution_repository import (
    PostgresExecutionRepository,
)
from app.services.task_dispatcher import TaskDispatcher
from app.workers.result_queue import TaskResultQueue
from app.workers.workflow_coordinator import WorkflowCoordinator
from app.workflows.execution import WorkflowExecution
from app.workflows.workflow import Workflow


class DistributedWorkflowExecutor:
    def __init__(
        self,
        dispatcher: TaskDispatcher,
        result_queue: TaskResultQueue,
        execution_repository: PostgresExecutionRepository | None = None,
    ):
        self.coordinator = WorkflowCoordinator(
            dispatcher=dispatcher,
            result_queue=result_queue,
        )

        self.execution_repository = execution_repository

    def start(
        self,
        workflow: Workflow,
        inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        workflow.validate()

        execution = WorkflowExecution(workflow)

        self.coordinator.dispatch_ready_steps(
            execution,
            inputs=inputs,
        )

        if self.execution_repository is not None:
            self.execution_repository.save(execution)

        return execution

    def process_result(
        self,
        execution: WorkflowExecution,
        result: dict[str, Any],
    ) -> WorkflowExecution:
        self.coordinator.process_result(
            execution,
            result,
        )

        if self.execution_repository is not None:
            self.execution_repository.save(execution)

        return execution