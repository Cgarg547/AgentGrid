import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.services.execution_checkpoint_repository import (
    ExecutionCheckpointRepository,
)
from app.services.execution_recovery_service import (
    ExecutionRecoveryService,
)


def test_recovery_service_returns_latest_checkpoint():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    execution_id = str(uuid.uuid4())

    with SessionLocal() as session:
        repository = ExecutionCheckpointRepository(
            session
        )

        repository.save(
            execution_id=execution_id,
            step_name="research",
            status="completed",
            state={
                "step_statuses": {
                    "research": "completed",
                    "analysis": "pending",
                    "report": "pending",
                },
                "step_results": {
                    "research": {
                        "findings": [
                            "finding-1",
                        ]
                    }
                },
            },
        )

        repository.save(
            execution_id=execution_id,
            step_name="analysis",
            status="completed",
            state={
                "step_statuses": {
                    "research": "completed",
                    "analysis": "completed",
                    "report": "pending",
                },
                "step_results": {
                    "research": {
                        "findings": [
                            "finding-1",
                        ]
                    },
                    "analysis": {
                        "summary": "analysis complete",
                    },
                },
            },
        )

        service = ExecutionRecoveryService(
            repository
        )

        recovered = service.recover_latest_state(
            execution_id
        )

        assert recovered is not None
        assert recovered["execution_id"] == execution_id
        assert recovered["step_name"] == "analysis"
        assert recovered["status"] == "completed"

        assert recovered["step_statuses"] == {
            "research": "completed",
            "analysis": "completed",
            "report": "pending",
        }

        assert recovered["step_results"] == {
            "research": {
                "findings": [
                    "finding-1",
                ]
            },
            "analysis": {
                "summary": "analysis complete",
            },
        }


def test_recovery_service_returns_none_when_no_checkpoint_exists():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    execution_id = str(uuid.uuid4())

    with SessionLocal() as session:
        repository = ExecutionCheckpointRepository(
            session
        )

        service = ExecutionRecoveryService(
            repository
        )

        recovered = service.recover_latest_state(
            execution_id
        )

        assert recovered is None


def test_workflow_execution_can_be_reconstructed_from_checkpoint():
    from app.workflows.examples import create_research_workflow
    from app.workflows.execution import WorkflowExecution
    from app.workflows.workflow_state import (
        StepStatus,
        WorkflowStatus,
    )

    workflow = create_research_workflow()

    execution = WorkflowExecution.from_checkpoint(
        workflow=workflow,
        execution_id="recovered-execution",
        status=WorkflowStatus.COMPLETED,
        step_statuses={
            "research": StepStatus.COMPLETED,
            "analysis": StepStatus.COMPLETED,
            "report": StepStatus.COMPLETED,
        },
        step_results={
            "research": {
                "findings": [
                    "finding-1",
                ]
            },
            "analysis": {
                "summary": "analysis complete",
            },
            "report": {
                "content": "report complete",
            },
        },
    )

    assert execution.execution_id == "recovered-execution"
    assert execution.status == WorkflowStatus.COMPLETED

    assert execution.get_completed_steps() == {
        "research",
        "analysis",
        "report",
    }

    assert execution.get_step_result(
        "research"
    ) == {
        "findings": [
            "finding-1",
        ]
    }

    assert execution.get_step_result(
        "analysis"
    ) == {
        "summary": "analysis complete",
    }