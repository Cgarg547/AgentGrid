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