from app.graph.nodes import (
    analysis_node,
    research_node,
    writer_node,
)
from app.runtime import AgentGridRuntime


def test_research_node_produces_findings():
    runtime = AgentGridRuntime()

    result = research_node(
        {
            "input": "Research AI orchestration",
        },
        runtime,
    )

    assert "research" in result
    assert result["research"]["findings"] == [
        "AI orchestration",
        "distributed workers",
    ]


def test_analysis_node_uses_research_state():
    runtime = AgentGridRuntime()

    result = analysis_node(
        {
            "research": {
                "findings": [
                    "finding one",
                    "finding two",
                ]
            }
        },
        runtime,
    )

    assert result["analysis"]["analysis"] == (
        "Analyzed 2 findings."
    )


def test_writer_node_uses_analysis_state():
    runtime = AgentGridRuntime()

    result = writer_node(
        {
            "analysis": {
                "analysis": "Analysis complete."
            }
        },
        runtime,
    )

    assert result["report"]["report"] == (
        "Analysis complete."
    )