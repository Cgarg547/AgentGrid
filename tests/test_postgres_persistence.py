from app.core.database import SessionLocal
from app.services.postgres_workflow_repository import (
    PostgresWorkflowRepository,
)
from app.workflows.examples import create_research_workflow


def test_workflow_persistence_round_trip():
    repository = PostgresWorkflowRepository(SessionLocal)

    workflow = create_research_workflow()

    repository.save(workflow)

    loaded = repository.get(workflow.name)

    assert loaded is not None
    assert loaded.name == workflow.name
    assert loaded.description == workflow.description

    assert [
        (
            step.name,
            step.agent_name,
            step.depends_on,
        )
        for step in loaded.steps
    ] == [
        (
            step.name,
            step.agent_name,
            step.depends_on,
        )
        for step in workflow.steps
    ]
