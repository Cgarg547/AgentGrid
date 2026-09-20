from typing import Any, Callable

from app.services.postgres_execution_repository import (
    PostgresExecutionRepository,
)
from app.workflows.execution import WorkflowExecution
from app.workflows.registry import WorkflowRegistry
from app.workflows.runner import WorkflowRunner


class WorkflowService:
    def __init__(
        self,
        workflow_registry: WorkflowRegistry,
        agent_handlers: dict[str, Callable[..., Any]],
        execution_repository: PostgresExecutionRepository,
    ):
        self.workflow_registry = workflow_registry
        self.agent_handlers = agent_handlers
        self.execution_repository = execution_repository

    def execute(
        self,
        workflow_name: str,
    ) -> WorkflowExecution:
        workflow = self.workflow_registry.get(workflow_name)

        execution = WorkflowExecution(workflow)

        runner = WorkflowRunner(
            execution,
            self.agent_handlers,
            on_state_change=self.execution_repository.save,
        )

        return runner.run()