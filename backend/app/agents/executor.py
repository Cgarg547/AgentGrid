import uuid
from typing import Any

from app.agents.agent import Agent
from app.security.approval import ApprovalRequest
from app.security.approval_store import ApprovalStore
from app.security.exceptions import ApprovalRequired
from app.security.policy import (
    PolicyDecision,
    ToolPolicy,
)
from app.tools.registry import ToolRegistry


class AgentExecutor:
    def __init__(
        self,
        agent: Agent,
        tool_registry: ToolRegistry,
        policies: dict[str, ToolPolicy] | None = None,
        approval_store: ApprovalStore | None = None,
    ):
        self.agent = agent
        self.tool_registry = tool_registry
        self.policies = policies or {}
        self.approval_store = (
            approval_store or ApprovalStore()
        )

    def execute_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Any:
        if not self.agent.can_use_tool(tool_name):
            raise PermissionError(
                f"Agent '{self.agent.name}' is not allowed "
                f"to use tool '{tool_name}'."
            )

        tool = self.tool_registry.get(tool_name)

        policy = self.policies.get(
            tool_name,
            ToolPolicy(tool_name=tool_name),
        )

        decision = policy.evaluate()

        if decision == PolicyDecision.DENY:
            raise PermissionError(
                f"Policy denied execution of tool "
                f"'{tool_name}'."
            )

        if decision == PolicyDecision.REQUIRE_APPROVAL:
            request_id = str(uuid.uuid4())

            request = ApprovalRequest(
                request_id=request_id,
                agent_name=self.agent.name,
                tool_name=tool_name,
                arguments=kwargs,
            )

            self.approval_store.save(request)

            raise ApprovalRequired(request_id)

        return tool.execute(**kwargs)


    def execute_approved_request(
        self,
        request_id: str,
    ) -> Any:
        request = self.approval_store.get(request_id)

        if request is None:
            raise KeyError(
                f"Approval request '{request_id}' not found."
            )

        if request.status.value != "approved":
            raise ValueError(
                f"Approval request '{request_id}' "
                f"is not approved."
            )

        if request.agent_name != self.agent.name:
            raise PermissionError(
                f"Approval request '{request_id}' "
                f"belongs to agent '{request.agent_name}'."
            )

        if not self.agent.can_use_tool(request.tool_name):
            raise PermissionError(
                f"Agent '{self.agent.name}' is not allowed "
                f"to use tool '{request.tool_name}'."
            )

        tool = self.tool_registry.get(request.tool_name)

        return tool.execute(**request.arguments)