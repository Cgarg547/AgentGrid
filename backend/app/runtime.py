from typing import Any

from app.agents.registry import AgentRegistry
from app.core.database import SessionLocal
from app.services.postgres_execution_repository import (
    PostgresExecutionRepository,
)
from app.services.workflow_service import WorkflowService
from app.tools.registry import ToolRegistry
from app.workflows.examples import create_research_workflow
from app.workflows.registry import WorkflowRegistry


class AgentGridRuntime:
    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.tool_registry = ToolRegistry()
        self.workflow_registry = WorkflowRegistry()

        self.execution_repository = (
            PostgresExecutionRepository(SessionLocal)
        )

        self.agent_handlers: dict[str, Any] = {
            "research-agent": self._research_agent,
            "analysis-agent": self._analysis_agent,
            "writer-agent": self._writer_agent,
        }

        self.workflow_service = WorkflowService(
            self.workflow_registry,
            self.agent_handlers,
            self.execution_repository,
        )

        self._register_workflows()

    def _register_workflows(self) -> None:
        self.workflow_registry.register(
            create_research_workflow()
        )

    def execute_workflow(self, workflow_name: str):
        execution = self.workflow_service.execute(
            workflow_name
        )

        self.execution_repository.save(execution)

        return execution

    def get_execution(self, execution_id: str):
        record = self.execution_repository.get(
            execution_id
        )

        if record is None:
            return None

        try:
            workflow = self.workflow_registry.get(
                record.workflow_name
            )
        except KeyError:
            return None

        from app.workflows.execution import WorkflowExecution
        from app.workflows.workflow_state import (
            StepStatus,
            WorkflowStatus,
        )

        execution = WorkflowExecution(
            workflow=workflow,
            execution_id=record.execution_id,
        )

        execution.status = WorkflowStatus(record.status)

        execution.step_statuses = {
            name: StepStatus(status)
            for name, status in record.step_statuses.items()
        }

        execution.step_results = record.step_results

        return execution

    def _research_agent(self, **kwargs: Any) -> dict:
        return {
            "findings": [
                "AI orchestration",
                "distributed workers",
            ]
        }

    def _analysis_agent(self, **kwargs: Any) -> dict:
        research = kwargs["inputs"]["research"]

        return {
            "analysis": (
                f"Analyzed {len(research['findings'])} findings."
            )
        }

    def _writer_agent(self, **kwargs: Any) -> dict:
        analysis = kwargs["inputs"]["analysis"]

        return {
            "report": analysis["analysis"],
        }