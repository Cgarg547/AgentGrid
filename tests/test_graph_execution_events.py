from app.core.database import SessionLocal
from app.graph.execution import LangGraphExecutionAdapter
from app.models.execution_event import ExecutionEvent
from app.runtime import AgentGridRuntime
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.workflows.examples import create_research_workflow


def test_langgraph_execution_persists_events():
    runtime = AgentGridRuntime()

    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(session)

        adapter = LangGraphExecutionAdapter(
            runtime=runtime,
            event_repository=repository,
        )

        workflow = create_research_workflow()

        execution = adapter.execute(
            workflow,
            {
                "input": "Research AI orchestration",
            },
        )

        events = (
            session.query(ExecutionEvent)
            .filter(
                ExecutionEvent.task_id
                == execution.execution_id
            )
            .order_by(
                ExecutionEvent.id.asc()
            )
            .all()
        )

        event_types = [
            event.event_type
            for event in events
        ]

        assert event_types == [
            "workflow.started",
            "step.started",
            "step.completed",
            "step.started",
            "step.completed",
            "step.started",
            "step.completed",
            "workflow.completed",
        ]

        assert all(
            event.task_id
            == execution.execution_id
            for event in events
        )

    finally:
        session.close()