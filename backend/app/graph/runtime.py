from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from app.graph.exceptions import GraphNodeExecutionError
from app.graph.nodes import (
    analysis_node,
    research_node,
    writer_node,
)
from app.graph.state import AgentGraphState
from app.runtime import AgentGridRuntime


def _run_node(
    node_name: str,
    node_function: Callable[
        [AgentGraphState, AgentGridRuntime],
        dict[str, Any],
    ],
    state: AgentGraphState,
    runtime: AgentGridRuntime,
    on_node_start: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    if on_node_start is not None:
        on_node_start(node_name)

    try:
        return node_function(
            state,
            runtime,
        )
    except Exception as exc:
        raise GraphNodeExecutionError(
            node_name=node_name,
            original_exception=exc,
        ) from exc


def build_agent_graph(
    runtime: AgentGridRuntime | None = None,
    on_node_start: Callable[[str], None] | None = None,
):
    runtime = runtime or AgentGridRuntime()

    graph = StateGraph(AgentGraphState)

    graph.add_node(
        "research",
        lambda state: _run_node(
            "research",
            research_node,
            state,
            runtime,
            on_node_start,
        ),
    )

    graph.add_node(
        "analysis",
        lambda state: _run_node(
            "analysis",
            analysis_node,
            state,
            runtime,
            on_node_start,
        ),
    )

    graph.add_node(
        "writer",
        lambda state: _run_node(
            "writer",
            writer_node,
            state,
            runtime,
            on_node_start,
        ),
    )

    graph.add_edge(
        START,
        "research",
    )

    graph.add_edge(
        "research",
        "analysis",
    )

    graph.add_edge(
        "analysis",
        "writer",
    )

    graph.add_edge(
        "writer",
        END,
    )

    return graph.compile()


def get_graph_structure() -> dict:
    return {
        "nodes": [
            "research",
            "analysis",
            "writer",
        ],
        "edges": [
            ["START", "research"],
            ["research", "analysis"],
            ["analysis", "writer"],
            ["writer", "END"],
        ],
    }