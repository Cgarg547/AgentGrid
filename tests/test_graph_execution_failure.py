import pytest

from app.core.database import SessionLocal
from app.graph.execution import LangGraphExecutionAdapter
from app.models.execution_event import ExecutionEvent
from app.runtime import AgentGridRuntime
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.workflows.examples import create_research_workflow


class FailingRuntime(AgentGridRuntime):
    def execute_agent(
        self,
        agent_name: str,
        **kwargs,
    ) -> dict:
        if agent_name == "analysis-agent":
            raise RuntimeError(
                "Analysis agent failed."
            )

        return super().execute_agent(
            agent_name,
            **kwargs,
        )


def test_langgraph_failure_persists_failure_event():
    runtime = FailingRuntime()

    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(session)

        adapter = LangGraphExecutionAdapter(
            runtime=runtime,
            event_repository=repository,
        )

        workflow = create_research_workflow()

        with pytest.raises(
            RuntimeError,
            match="Analysis agent failed.",
        ):
            adapter.execute(
                workflow,
                {
                    "input": "Research AI orchestration",
                },
            )

        latest_started_event = (
            session.query(ExecutionEvent)
            .filter(
                ExecutionEvent.event_type
                == "workflow.started"
            )
            .order_by(
                ExecutionEvent.id.desc()
            )
            .first()
        )

        assert latest_started_event is not None

        execution_events = (
            session.query(ExecutionEvent)
            .filter(
                ExecutionEvent.task_id
                == latest_started_event.task_id
            )
            .order_by(ExecutionEvent.id.asc())
            .all()
        )

        event_types = [
            event.event_type
            for event in execution_events
        ]

        assert event_types == [
            "workflow.started",
            "step.started",
            "step.completed",
            "step.started",
            "step.failed",
            "workflow.failed",
        ]

        step_failure_events = [
            event
            for event in execution_events
            if event.event_type == "step.failed"
        ]

        assert len(step_failure_events) == 1

        step_failure_event = (
            step_failure_events[0]
        )

        step_failure_data = (
            repository.deserialize_data(
                step_failure_event.data
            )
        )

        assert step_failure_data["step_name"] == (
            "analysis"
        )

        assert step_failure_data["node_name"] == (
            "analysis"
        )

        assert step_failure_data["error"] == (
            "Analysis agent failed."
        )

        workflow_failure_events = [
            event
            for event in execution_events
            if event.event_type == "workflow.failed"
        ]

        assert len(workflow_failure_events) == 1

        workflow_failure_event = (
            workflow_failure_events[0]
        )

        workflow_failure_data = (
            repository.deserialize_data(
                workflow_failure_event.data
            )
        )

        assert workflow_failure_data["workflow_name"] == (
            workflow.name
        )

        assert workflow_failure_data["error"] == (
            "Analysis agent failed."
        )

    finally:
        session.close()