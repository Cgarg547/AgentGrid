from app.graph.execution import LangGraphExecutionAdapter
from app.runtime import AgentGridRuntime
from app.workflows.examples import create_research_workflow
from app.workflows.workflow_state import (
    StepStatus,
    WorkflowStatus,
)


def test_langgraph_execution_completes_each_step():
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

    assert execution.step_statuses["research"] == (
        StepStatus.COMPLETED
    )

    assert execution.step_statuses["analysis"] == (
        StepStatus.COMPLETED
    )

    assert execution.step_statuses["report"] == (
        StepStatus.COMPLETED
    )