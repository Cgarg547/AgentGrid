from app.graph.runtime import (
    build_agent_graph,
    get_graph_structure,
)
from app.runtime import AgentGridRuntime


def test_agent_graph_executes_full_pipeline():
    runtime = AgentGridRuntime()

    graph = build_agent_graph(runtime)

    result = graph.invoke(
        {
            "input": "Research AI orchestration",
        }
    )

    assert result["input"] == "Research AI orchestration"

    assert result["research"]["findings"] == [
        "AI orchestration",
        "distributed workers",
    ]

    assert result["analysis"]["analysis"] == (
        "Analyzed 2 findings."
    )

    assert result["report"]["report"] == (
        "Analyzed 2 findings."
    )


def test_graph_structure_is_inspectable():
    structure = get_graph_structure()

    assert structure["nodes"] == [
        "research",
        "analysis",
        "writer",
    ]

    assert structure["edges"] == [
        ["START", "research"],
        ["research", "analysis"],
        ["analysis", "writer"],
        ["writer", "END"],
    ]

def test_agent_graph_skips_completed_steps_on_resume():
    from app.graph.runtime import build_agent_graph

    graph = build_agent_graph()

    updates = list(
        graph.stream(
            {
                "input": "Resume workflow",
                "completed_steps": [
                    "research",
                    "analysis",
                ],
                "research": {
                    "findings": [
                        "existing finding",
                    ]
                },
                "analysis": {
                    "analysis": "existing analysis",
                },
            }
        )
    )

    executed_nodes = [
        node_name
        for update in updates
        for node_name in update.keys()
    ]

    assert executed_nodes == [
        "writer",
    ]