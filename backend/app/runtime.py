from typing import Any

from app.agents.agent import Agent
from app.agents.executor import AgentExecutor
from app.agents.registry import AgentRegistry
from app.core.database import SessionLocal
from app.security.approval_store import ApprovalStore
from app.services.postgres_execution_repository import (
    PostgresExecutionRepository,
)
from app.services.postgres_workflow_repository import (
    PostgresWorkflowRepository,
)
from app.services.execution_recovery_service import (
    ExecutionRecoveryService,
)
from app.services.execution_checkpoint_repository import (
    ExecutionCheckpointRepository,
)
from app.services.distributed_workflow_executor import (
    DistributedWorkflowExecutor,
)
from app.services.workflow_schedule_repository import (
    WorkflowScheduleRepository,
)
from app.services.workflow_schedule_service import (
    WorkflowScheduleService,
)
from app.services.workflow_scheduler_loop import (
    WorkflowSchedulerLoop,
)
from app.services.workflow_scheduler import WorkflowScheduler
from app.services.task_dispatcher import TaskDispatcher
from app.workers.queue import TaskQueue
from app.workers.result_queue import TaskResultQueue
from app.services.workflow_service import WorkflowService
from app.tools.registry import ToolRegistry
from app.tools.tool import Tool
from app.workflows.examples import create_research_workflow
from app.workflows.registry import WorkflowRegistry


class AgentGridRuntime:
    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.tool_registry = ToolRegistry()
        self.workflow_registry = WorkflowRegistry()

        self.approval_store = ApprovalStore()

        self.execution_repository = (
            PostgresExecutionRepository(SessionLocal)
        )

        self.workflow_repository = (
            PostgresWorkflowRepository(SessionLocal)
        )
        self.workflow_schedule_repository = (
            WorkflowScheduleRepository(SessionLocal)
        )
        self.workflow_schedule_service = WorkflowScheduleService(
            self.workflow_schedule_repository
        )
        self.distributed_task_queue = TaskQueue(
            "agentgrid:workflow:tasks"
        )

        self.distributed_result_queue = TaskResultQueue(
            "agentgrid:workflow:results"
        )

        self.distributed_workflow_executor = (
            DistributedWorkflowExecutor(
                dispatcher=TaskDispatcher(
                    self.distributed_task_queue
                ),
                result_queue=self.distributed_result_queue,
                execution_repository=self.execution_repository,
            )
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

        self.workflow_scheduler = WorkflowScheduler(
            repository=self.workflow_schedule_repository,
            workflow_executor=self.execute_workflow_distributed,
        )

        self.workflow_scheduler_loop = WorkflowSchedulerLoop(
            scheduler=self.workflow_scheduler,
        )

        self._register_agents()
        self._register_tools()
        self._register_workflows()

    def _register_agents(self) -> None:
        self.agent_registry.register(
            Agent(
                name="researcher",
                description="Research agent",
                allowed_tools=["send_email"],
            )
        )

    def _register_tools(self) -> None:
        self.tool_registry.register(
            Tool(
                name="send_email",
                description="Send an email",
                handler=lambda **kwargs: {
                    "message": "email sent",
                    "arguments": kwargs,
                },
            )
        )

    def get_approval_executor(self) -> AgentExecutor:
        agent = self.agent_registry.get("researcher")

        return AgentExecutor(
            agent=agent,
            tool_registry=self.tool_registry,
            approval_store=self.approval_store,
        )

    def _register_workflows(self) -> None:
        workflow = create_research_workflow()

        self.workflow_repository.save(workflow)
        self._load_persisted_workflows()

    def _load_persisted_workflows(self) -> None:
        workflows = self.workflow_repository.list()

        for workflow in workflows:
            if workflow.name not in {
                existing.name
                for existing in self.workflow_registry.list()
            }:
                self.workflow_registry.register(workflow)

    def execute_workflow(
        self,
        workflow_name: str,
    ):
        workflow = self.workflow_registry.get(
            workflow_name
        )

        from app.graph.execution import (
            LangGraphExecutionAdapter,
        )

        from app.services.execution_event_repository import (
            ExecutionEventRepository,
        )

        with SessionLocal() as session:
            event_repository = ExecutionEventRepository(
                session
            )

            checkpoint_repository = (
                ExecutionCheckpointRepository(session)
            )

            adapter = LangGraphExecutionAdapter(
                runtime=self,
                event_repository=event_repository,
                checkpoint_repository=checkpoint_repository,
            )

            execution = adapter.execute(
                workflow=workflow,
                inputs={},
            )

        self.execution_repository.save(execution)

        return execution

    def execute_workflow_distributed(
        self,
        workflow_name: str,
        inputs: dict[str, Any] | None = None,
    ):
        workflow = self.workflow_registry.get(
            workflow_name
        )

        return self.distributed_workflow_executor.start(
            workflow=workflow,
            inputs=inputs,
        )

    def get_execution(
        self,
        execution_id: str,
    ):
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

        execution.status = WorkflowStatus(
            record.status
        )

        execution.step_statuses = {
            name: StepStatus(status)
            for name, status in record.step_statuses.items()
        }

        execution.step_results = record.step_results

        return execution

    def recover_distributed_execution(
        self,
        execution_id: str,
    ):
        record = self.execution_repository.get(
            execution_id
        )

        if record is None:
            return None

        workflow = self.workflow_registry.get(
            record.workflow_name
        )

        recovery_service = ExecutionRecoveryService(
            execution_repository=self.execution_repository,
        )

        return recovery_service.recover_distributed_execution(
            workflow=workflow,
            execution_id=execution_id,
        )

    def pause_execution(
        self,
        execution_id: str,
    ):
        execution = self.get_execution(
            execution_id
        )

        if execution is None:
            return None

        execution.pause()

        self.execution_repository.save(
            execution
        )

        return execution

    def resume_execution(
        self,
        execution_id: str,
    ):
        execution = self.get_execution(
            execution_id
        )

        if execution is None:
            return None

        execution.resume()

        self.distributed_workflow_executor.coordinator.dispatch_ready_steps(
            execution
        )

        self.execution_repository.save(
            execution
        )

        return execution

    def execute_agent(
        self,
        agent_name: str,
        **kwargs: Any,
    ) -> dict:
        handler = self.agent_handlers.get(agent_name)

        if handler is None:
            raise KeyError(
                f"Agent '{agent_name}' is not registered."
            )

        return handler(**kwargs)

    def _research_agent(
        self,
        **kwargs: Any,
    ) -> dict:
        return {
            "findings": [
                "AI orchestration",
                "distributed workers",
            ]
        }

    def _analysis_agent(
        self,
        **kwargs: Any,
    ) -> dict:
        research = kwargs["inputs"]["research"]

        return {
            "analysis": (
                f"Analyzed "
                f"{len(research['findings'])} findings."
            )
        }

    def _writer_agent(
        self,
        **kwargs: Any,
    ) -> dict:
        analysis = kwargs["inputs"]["analysis"]

        return {
            "report": analysis["analysis"],
        }

    def start_scheduler(self) -> None:
        self.workflow_scheduler_loop.start()

    def stop_scheduler(self) -> None:
        self.workflow_scheduler_loop.stop()