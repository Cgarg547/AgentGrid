import pytest

from app.agents.agent import Agent
from app.agents.executor import AgentExecutor
from app.security.approval_store import ApprovalStore
from app.security.exceptions import ApprovalRequired
from app.security.policy import ToolPolicy
from app.tools.registry import ToolRegistry
from app.tools.tool import Tool


def create_executor(
    policy: ToolPolicy | None = None,
    approval_store: ApprovalStore | None = None,
):
    agent = Agent(
        name="researcher",
        description="Research agent",
        allowed_tools=["search"],
    )

    registry = ToolRegistry()

    registry.register(
        Tool(
            name="search",
            description="Search tool",
            handler=lambda **kwargs: {
                "message": "search executed",
            },
        )
    )

    policies = {}

    if policy is not None:
        policies["search"] = policy

    return AgentExecutor(
        agent=agent,
        tool_registry=registry,
        policies=policies,
        approval_store=approval_store,
    )


def test_executor_allows_tool_when_policy_allows():
    executor = create_executor(
        ToolPolicy(
            tool_name="search",
        )
    )

    result = executor.execute_tool(
        "search",
        query="AgentGrid",
    )

    assert result == {
        "message": "search executed",
    }


def test_executor_denies_tool_when_policy_denies():
    executor = create_executor(
        ToolPolicy(
            tool_name="search",
            allowed=False,
        )
    )

    with pytest.raises(
        PermissionError,
        match="Policy denied execution",
    ):
        executor.execute_tool(
            "search",
            query="AgentGrid",
        )


def test_executor_requires_approval_when_policy_requires_it():
    approval_store = ApprovalStore(
        key_prefix="test-executor-approval"
    )

    executor = create_executor(
        ToolPolicy(
            tool_name="search",
            require_approval=True,
        ),
        approval_store=approval_store,
    )

    try:
        with pytest.raises(
            ApprovalRequired
        ) as exc_info:
            executor.execute_tool(
                "search",
                query="AgentGrid",
            )

        request_id = exc_info.value.request_id

        request = approval_store.get(
            request_id
        )

        assert request is not None
        assert request.status.value == "pending"

    finally:
        if "request_id" in locals():
            approval_store.delete(request_id)


def test_executor_defaults_to_allow_when_no_policy_exists():
    executor = create_executor()

    result = executor.execute_tool(
        "search",
        query="AgentGrid",
    )

    assert result == {
        "message": "search executed",
    }


def test_executor_still_enforces_agent_permission():
    agent = Agent(
        name="restricted-agent",
        description="Restricted agent",
        allowed_tools=[],
    )

    registry = ToolRegistry()

    registry.register(
        Tool(
            name="search",
            description="Search tool",
            handler=lambda **kwargs: {
                "message": "search executed",
            },
        )
    )

    executor = AgentExecutor(
        agent=agent,
        tool_registry=registry,
    )

    with pytest.raises(
        PermissionError,
        match="is not allowed to use tool",
    ):
        executor.execute_tool(
            "search",
            query="AgentGrid",
        )


def test_executor_creates_approval_request():
    approval_store = ApprovalStore(
        key_prefix="test-executor-approval"
    )

    executor = create_executor(
        ToolPolicy(
            tool_name="search",
            require_approval=True,
        ),
        approval_store=approval_store,
    )

    try:
        with pytest.raises(
            ApprovalRequired
        ) as exc_info:
            executor.execute_tool(
                "search",
                query="AgentGrid",
            )

        request_id = exc_info.value.request_id

        request = approval_store.get(
            request_id
        )

        assert request is not None
        assert request.request_id == request_id
        assert request.agent_name == "researcher"
        assert request.tool_name == "search"
        assert request.status.value == "pending"
        assert request.arguments == {
            "query": "AgentGrid",
        }

    finally:
        if "request_id" in locals():
            approval_store.delete(request_id)


def test_executor_executes_approved_request():
    approval_store = ApprovalStore(
        key_prefix="test-executor-approved"
    )

    executor = create_executor(
        ToolPolicy(
            tool_name="search",
            require_approval=True,
        ),
        approval_store=approval_store,
    )

    try:
        with pytest.raises(
            ApprovalRequired
        ) as exc_info:
            executor.execute_tool(
                "search",
                query="AgentGrid",
            )

        request_id = exc_info.value.request_id

        approval_store.approve(request_id)

        result = executor.execute_approved_request(
            request_id
        )

        assert result == {
            "message": "search executed",
        }

    finally:
        if "request_id" in locals():
            approval_store.delete(request_id)