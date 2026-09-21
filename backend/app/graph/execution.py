from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.graph.exceptions import GraphNodeExecutionError
from app.graph.runtime import build_agent_graph
from app.runtime import AgentGridRuntime
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.services.execution_checkpoint_repository import (
    ExecutionCheckpointRepository,
)
from app.workers.events import WorkerEvent
from app.workflows.execution import WorkflowExecution
from app.workflows.workflow import Workflow
from app.workflows.workflow_state import WorkflowStatus


class LangGraphExecutionAdapter:
    def __init__(
        self,
        runtime: AgentGridRuntime,
        event_repository: ExecutionEventRepository | None = None,
        checkpoint_repository: ExecutionCheckpointRepository | None = None,
    ):
        self.runtime = runtime
        self.event_repository = event_repository
        self.checkpoint_repository = checkpoint_repository
        self._step_started_at: dict[str, float] = {}

    def execute(
        self,
        workflow: Workflow,
        inputs: dict[str, Any],
    ) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow=workflow,
        )

        self._step_started_at = {}

        workflow_started_at = perf_counter()

        self._record_event(
            event_type="workflow.started",
            execution_id=execution.execution_id,
            data={
                "workflow_name": workflow.name,
                "started_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            },
        )

        graph = build_agent_graph(
            runtime=self.runtime,
            on_node_start=lambda node_name: (
                self._handle_node_start(
                    execution,
                    node_name,
                )
            ),
        )

        try:
            execution.status = WorkflowStatus.RUNNING

            for update in graph.stream(inputs):
                self._process_graph_update(
                    execution,
                    update,
                )

            workflow_duration_ms = (
                perf_counter() - workflow_started_at
            ) * 1000

            self._record_event(
                event_type="workflow.completed",
                execution_id=execution.execution_id,
                data={
                    "workflow_name": workflow.name,
                    "status": execution.status.value,
                    "completed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "duration_ms": workflow_duration_ms,
                },
            )

        except GraphNodeExecutionError as exc:
            execution.status = WorkflowStatus.FAILED

            step_name = self._get_step_name(
                exc.node_name
            )

            execution.mark_step_failed(step_name)

            step_duration_ms = self._get_step_duration_ms(
                step_name
            )

            self._record_event(
                event_type="step.failed",
                execution_id=execution.execution_id,
                data={
                    "step_name": step_name,
                    "node_name": exc.node_name,
                    "error": str(
                        exc.original_exception
                    ),
                    "duration_ms": step_duration_ms,
                },
            )

            self._record_event(
                event_type="workflow.failed",
                execution_id=execution.execution_id,
                data={
                    "workflow_name": workflow.name,
                    "error": str(
                        exc.original_exception
                    ),
                    "duration_ms": (
                        perf_counter()
                        - workflow_started_at
                    ) * 1000,
                },
            )

            raise exc.original_exception

        except Exception as exc:
            execution.status = WorkflowStatus.FAILED

            self._record_event(
                event_type="workflow.failed",
                execution_id=execution.execution_id,
                data={
                    "workflow_name": workflow.name,
                    "error": str(exc),
                    "duration_ms": (
                        perf_counter()
                        - workflow_started_at
                    ) * 1000,
                },
            )

            raise

        return execution

    def _handle_node_start(
        self,
        execution: WorkflowExecution,
        node_name: str,
    ) -> None:
        step_name = self._get_step_name(
            node_name
        )

        execution.mark_step_running(step_name)

        self._step_started_at[step_name] = (
            perf_counter()
        )

        self._record_event(
            event_type="step.started",
            execution_id=execution.execution_id,
            data={
                "step_name": step_name,
                "node_name": node_name,
                "started_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            },
        )

    def _process_graph_update(
        self,
        execution: WorkflowExecution,
        update: dict[str, Any],
    ) -> None:
        for node_name, node_result in update.items():
            step_name = self._get_step_name(
                node_name
            )

            execution.mark_step_completed(
                step_name,
                self._unwrap_node_result(
                    node_name,
                    node_result,
                ),
            )

            self._save_checkpoint(
                execution=execution,
                step_name=step_name,
            )

            duration_ms = self._get_step_duration_ms(
                step_name
            )

            self._record_event(
                event_type="step.completed",
                execution_id=execution.execution_id,
                data={
                    "step_name": step_name,
                    "node_name": node_name,
                    "completed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "duration_ms": duration_ms,
                },
            )

        return None

    def _save_checkpoint(
        self,
        execution: WorkflowExecution,
        step_name: str,
    ) -> None:
        if self.checkpoint_repository is None:
            return

        self.checkpoint_repository.save(
            execution_id=execution.execution_id,
            step_name=step_name,
            status=execution.step_statuses[
                step_name
            ].value,
            state={
                "step_statuses": {
                    name: status.value
                    for name, status
                    in execution.step_statuses.items()
                },
                "step_results": execution.step_results,
            },
        )
        
    def _get_step_duration_ms(
        self,
        step_name: str,
    ) -> float:
        started_at = self._step_started_at.pop(
            step_name,
            None,
        )

        if started_at is None:
            return 0.0

        return (
            perf_counter() - started_at
        ) * 1000

    def _record_event(
        self,
        event_type: str,
        execution_id: str,
        data: dict[str, Any],
    ) -> None:
        if self.event_repository is None:
            return

        event = WorkerEvent.create(
            event_type=event_type,
            task_id=execution_id,
            data=data,
        )

        self.event_repository.save(event)

    @staticmethod
    def _get_step_name(
        node_name: str,
    ) -> str:
        mapping = {
            "research": "research",
            "analysis": "analysis",
            "writer": "report",
        }

        step_name = mapping.get(node_name)

        if step_name is None:
            raise KeyError(
                "No workflow step mapping exists "
                f"for LangGraph node '{node_name}'."
            )

        return step_name

    @staticmethod
    def _unwrap_node_result(
        node_name: str,
        node_result: Any,
    ) -> Any:
        result_key = {
            "research": "research",
            "analysis": "analysis",
            "writer": "report",
        }.get(node_name)

        if result_key is None:
            raise KeyError(
                "No result mapping exists for "
                f"LangGraph node '{node_name}'."
            )

        if isinstance(node_result, dict):
            return node_result.get(result_key)

        return node_result