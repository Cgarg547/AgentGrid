from typing import Any

from app.agents.agent import Agent
from app.tools.registry import ToolRegistry


class AgentExecutor:
    def __init__(self, agent: Agent, tool_registry: ToolRegistry):
        self.agent = agent
        self.tool_registry = tool_registry

    def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        if not self.agent.can_use_tool(tool_name):
            raise PermissionError(
                f"Agent '{self.agent.name}' is not allowed "
                f"to use tool '{tool_name}'."
            )

        tool = self.tool_registry.get(tool_name)

        return tool.execute(**kwargs)