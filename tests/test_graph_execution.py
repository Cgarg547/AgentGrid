from app.graph.execution import LangGraphExecutionAdapter
from app.runtime import AgentGridRuntime
from app.workflows.examples import create_research_workflow
from app.workflows.workflow_state import (
    StepStatus,
    WorkflowStatus,
)


def test_langgraph_execution_creates_workflow_execution():
    runtime = AgentGridRuntime()

    adapter = LangGraphExecutionAdapter(runtime)

    workflow = create_research_workflow()

    execution = adapter.execute(
        workflow,
        {
            "input": "Research AI orchestration",
        },
    )

    assert execution.status == WorkflowStatus.COMPLETED

    assert execution.step_statuses == {
        "research": StepStatus.COMPLETED,
        "analysis": StepStatus.COMPLETED,
        "report": StepStatus.COMPLETED,
    }

    assert execution.step_results["research"] == {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

    assert execution.step_results["analysis"] == {
        "analysis": "Analyzed 2 findings."
    }

    assert execution.step_results["report"] == {
        "report": "Analyzed 2 findings."
    }

def test_langgraph_execution_resumes_from_checkpoint():
    from app.core.database import SessionLocal
    from app.services.execution_checkpoint_repository import (
        ExecutionCheckpointRepository,
    )
    from app.workflows.examples import create_research_workflow

    runtime = AgentGridRuntime()
    workflow = create_research_workflow()

    execution_id = "resume-test-execution"

    with SessionLocal() as session:
        checkpoint_repository = (
            ExecutionCheckpointRepository(session)
        )

        checkpoint_repository.save(
            execution_id=execution_id,
            step_name="analysis",
            status="completed",
            state={
                "step_statuses": {
                    "research": "completed",
                    "analysis": "completed",
                    "report": "pending",
                },
                "step_results": {
                    "research": {
                        "findings": [
                            "AI orchestration",
                            "distributed workers",
                        ]
                    },
                    "analysis": {
                        "analysis": "analysis complete",
                    },
                },
            },
        )

        adapter = LangGraphExecutionAdapter(
            runtime=runtime,
            checkpoint_repository=checkpoint_repository,
        )

        execution = adapter.resume(
            workflow=workflow,
            execution_id=execution_id,
            inputs={
                "input": "Resume AI orchestration workflow",
            },
        )

        assert execution.execution_id == execution_id

        assert execution.status == WorkflowStatus.COMPLETED

        assert execution.step_statuses == {
            "research": StepStatus.COMPLETED,
            "analysis": StepStatus.COMPLETED,
            "report": StepStatus.COMPLETED,
        }

        assert "research" in execution.step_results
        assert "analysis" in execution.step_results
        assert "report" in execution.step_results