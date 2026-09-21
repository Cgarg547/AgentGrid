from typing import Any

from app.graph.execution import LangGraphExecutionAdapter
from app.runtime import AgentGridRuntime
from app.workflows.examples import create_research_workflow


class RecordingRuntime(AgentGridRuntime):
    def __init__(self):
        self.execution_order: list[str] = []
        super().__init__()

    def execute_agent(
        self,
        agent_name: str,
        **kwargs: Any,
    ) -> dict:
        self.execution_order.append(agent_name)

        return super().execute_agent(
            agent_name,
            **kwargs,
        )


def test_langgraph_executes_agents_in_workflow_order():
    runtime = RecordingRuntime()

    adapter = LangGraphExecutionAdapter(runtime)

    workflow = create_research_workflow()

    execution = adapter.execute(
        workflow,
        {
            "input": "Research AI orchestration",
        },
    )

    assert execution.status.value == "completed"

    assert runtime.execution_order == [
        "research-agent",
        "analysis-agent",
        "writer-agent",
    ]