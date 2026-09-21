from app.graph.state import AgentGraphState


def test_agent_graph_state_supports_shared_state():
    state: AgentGraphState = {
        "input": "Research AI orchestration",
        "research": {
            "findings": [
                "distributed workers",
                "workflow orchestration",
            ]
        },
        "analysis": {
            "summary": "The findings describe an orchestration system."
        },
        "report": {
            "content": "Final report",
        },
    }

    assert state["input"] == "Research AI orchestration"
    assert len(state["research"]["findings"]) == 2
    assert state["analysis"]["summary"]
    assert state["report"]["content"] == "Final report"