from app.workflows.workflow import Workflow, WorkflowStep


def create_research_workflow() -> Workflow:
    workflow = Workflow(
        name="research-pipeline",
        description="Research, analyze, and produce a report.",
    )

    workflow.add_step(
        WorkflowStep(
            name="research",
            agent_name="research-agent",
        )
    )

    workflow.add_step(
        WorkflowStep(
            name="analysis",
            agent_name="analysis-agent",
            depends_on=["research"],
        )
    )

    workflow.add_step(
        WorkflowStep(
            name="report",
            agent_name="writer-agent",
            depends_on=["analysis"],
        )
    )

    return workflow