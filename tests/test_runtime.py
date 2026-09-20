from app.runtime import AgentGridRuntime


def test_runtime_executes_persisted_workflow():
    runtime = AgentGridRuntime()

    execution = runtime.execute_workflow(
        "research-pipeline"
    )

    assert execution.status.value == "completed"

    assert execution.step_results["research"]["findings"] == [
        "AI orchestration",
        "distributed workers",
    ]

    assert execution.step_results["analysis"]["analysis"] == (
        "Analyzed 2 findings."
    )

    assert execution.step_results["report"]["report"] == (
        "Analyzed 2 findings."
    )

    persisted = runtime.get_execution(
        execution.execution_id
    )

    assert persisted is not None
    assert persisted.status.value == "completed"
    assert persisted.workflow.name == "research-pipeline"
