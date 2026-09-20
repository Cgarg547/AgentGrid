from app.workflows.execution import WorkflowExecution
from app.workflows.examples import create_research_workflow
from app.workflows.runner import WorkflowRunner


def test_research_workflow_completes():
    workflow = create_research_workflow()
    execution = WorkflowExecution(workflow)

    handlers = {
        "research-agent": lambda **kwargs: {
            "findings": ["AI orchestration", "distributed workers"]
        },
        "analysis-agent": lambda **kwargs: {
            "analysis": (
                f"Analyzed "
                f"{len(kwargs['inputs']['research']['findings'])} findings."
            )
        },
        "writer-agent": lambda **kwargs: {
            "report": kwargs["inputs"]["analysis"]["analysis"]
        },
    }

    runner = WorkflowRunner(
        execution=execution,
        agent_handlers=handlers,
    )

    result = runner.run()

    assert result.status.value == "completed"
    assert result.step_results["research"]["findings"] == [
        "AI orchestration",
        "distributed workers",
    ]
    assert result.step_results["analysis"]["analysis"] == (
        "Analyzed 2 findings."
    )
    assert result.step_results["report"]["report"] == (
        "Analyzed 2 findings."
    )
