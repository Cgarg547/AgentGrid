from app.runtime import AgentGridRuntime


def test_runtime_can_execute_registered_agent():
    runtime = AgentGridRuntime()

    result = runtime.execute_agent(
        "research-agent"
    )

    assert result == {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }


def test_runtime_rejects_unknown_agent():
    runtime = AgentGridRuntime()

    try:
        runtime.execute_agent("unknown-agent")
    except KeyError as exc:
        assert "unknown-agent" in str(exc)
    else:
        raise AssertionError(
            "Expected KeyError for unknown agent."
        )