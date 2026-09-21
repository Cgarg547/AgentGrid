from app.core.database import SessionLocal
from app.graph.execution import LangGraphExecutionAdapter
from app.runtime import AgentGridRuntime
from app.services.execution_checkpoint_repository import (
    ExecutionCheckpointRepository,
)
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.workflows.examples import create_research_workflow


def test_langgraph_execution_persists_checkpoints():
    runtime = AgentGridRuntime()
    workflow = create_research_workflow()

    with SessionLocal() as session:
        event_repository = ExecutionEventRepository(
            session
        )

        checkpoint_repository = (
            ExecutionCheckpointRepository(session)
        )

        adapter = LangGraphExecutionAdapter(
            runtime=runtime,
            event_repository=event_repository,
            checkpoint_repository=checkpoint_repository,
        )

        execution = adapter.execute(
            workflow=workflow,
            inputs={
                "input": "Research AI orchestration",
            },
        )

        checkpoints = (
            checkpoint_repository.list_by_execution(
                execution.execution_id
            )
        )

        assert len(checkpoints) == 3

        assert [
            checkpoint.step_name
            for checkpoint in checkpoints
        ] == [
            "research",
            "analysis",
            "report",
        ]

        assert [
            checkpoint.status
            for checkpoint in checkpoints
        ] == [
            "completed",
            "completed",
            "completed",
        ]

        research_state = (
            checkpoint_repository.deserialize_state(
                checkpoints[0].state
            )
        )

        analysis_state = (
            checkpoint_repository.deserialize_state(
                checkpoints[1].state
            )
        )

        report_state = (
            checkpoint_repository.deserialize_state(
                checkpoints[2].state
            )
        )

        assert research_state["step_statuses"] == {
            "research": "completed",
            "analysis": "pending",
            "report": "pending",
        }

        assert research_state["step_results"]["research"] == {
            "findings": [
                "AI orchestration",
                "distributed workers",
            ],
        }

        assert analysis_state["step_statuses"] == {
            "research": "completed",
            "analysis": "completed",
            "report": "pending",
        }

        assert "research" in analysis_state["step_results"]
        assert "analysis" in analysis_state["step_results"]

        assert report_state["step_statuses"] == {
            "research": "completed",
            "analysis": "completed",
            "report": "completed",
        }

        assert "research" in report_state["step_results"]
        assert "analysis" in report_state["step_results"]
        assert "report" in report_state["step_results"]