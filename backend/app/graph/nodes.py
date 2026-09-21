from typing import Any

from app.graph.state import AgentGraphState
from app.runtime import AgentGridRuntime


def research_node(
    state: AgentGraphState,
    runtime: AgentGridRuntime,
) -> dict[str, Any]:
    """Execute the AgentGrid research agent."""

    result = runtime.execute_agent(
        "research-agent",
        inputs=state,
    )

    return {
        "research": result,
    }


def analysis_node(
    state: AgentGraphState,
    runtime: AgentGridRuntime,
) -> dict[str, Any]:
    """Execute the AgentGrid analysis agent."""

    result = runtime.execute_agent(
        "analysis-agent",
        inputs=state,
    )

    return {
        "analysis": result,
    }


def writer_node(
    state: AgentGraphState,
    runtime: AgentGridRuntime,
) -> dict[str, Any]:
    """Execute the AgentGrid writer agent."""

    result = runtime.execute_agent(
        "writer-agent",
        inputs=state,
    )

    return {
        "report": result,
    }