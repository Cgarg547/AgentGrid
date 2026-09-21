from typing import Any

from app.runtime import AgentGridRuntime


class WorkflowTaskHandler:
    def __init__(
        self,
        runtime: AgentGridRuntime,
        agent_name: str,
    ):
        self.runtime = runtime
        self.agent_name = agent_name

    def handle(
        self,
        *,
        step_name: str,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        return self.runtime.execute_agent(
            self.agent_name,
            inputs=inputs,
            step_name=step_name,
        )