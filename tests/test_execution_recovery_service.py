import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.services.postgres_execution_repository import (
    PostgresExecutionRepository,
)
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


def test_recovery_service_reconstructs_partial_workflow_execution():
    from app.workflows.examples import create_research_workflow
    from app.workflows.execution import WorkflowExecution
    from app.workflows.workflow_state import StepStatus, WorkflowStatus

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

        workflow = create_research_workflow()

        service = ExecutionRecoveryService(
            repository
        )

        recovered = service.recover_execution(
            workflow=workflow,
            execution_id=execution_id,
        )

        assert isinstance(
            recovered,
            WorkflowExecution,
        )

        assert recovered is not None
        assert recovered.execution_id == execution_id
        assert recovered.status == WorkflowStatus.RUNNING

        assert recovered.step_statuses == {
            "research": StepStatus.COMPLETED,
            "analysis": StepStatus.COMPLETED,
            "report": StepStatus.PENDING,
        }

        assert recovered.get_completed_steps() == {
            "research",
            "analysis",
        }

        assert recovered.get_step_result(
            "research"
        ) == {
            "findings": [
                "finding-1",
            ]
        }

        assert recovered.get_step_result(
            "analysis"
        ) == {
            "summary": "analysis complete",
        }

        assert [
            step.name
            for step in recovered.get_ready_steps()
        ] == [
            "report",
        ]

def test_recovery_service_reconstructs_distributed_execution():
    from app.workflows.examples import create_research_workflow
    from app.workflows.execution import WorkflowExecution
    from app.workflows.workflow_state import (
        StepStatus,
        WorkflowStatus,
    )

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

    workflow = create_research_workflow()

    execution = WorkflowExecution(
        workflow=workflow,
        execution_id=execution_id,
    )

    execution.step_statuses["research"] = (
        StepStatus.COMPLETED
    )

    execution.step_statuses["analysis"] = (
        StepStatus.COMPLETED
    )

    execution.step_statuses["report"] = (
        StepStatus.RUNNING
    )

    execution.step_results["research"] = {
        "findings": [
            "AI orchestration",
            "distributed workers",
        ]
    }

    execution.step_results["analysis"] = {
        "analysis": "Analyzed 2 findings.",
    }

    execution.status = WorkflowStatus.RUNNING

    with SessionLocal() as session:
        checkpoint_repository = (
            ExecutionCheckpointRepository(session)
        )

        execution_repository = (
            PostgresExecutionRepository(SessionLocal)
        )

        service = ExecutionRecoveryService(
            checkpoint_repository=checkpoint_repository,
            execution_repository=execution_repository,
        )

        execution_repository.save(execution)

        recovered = service.recover_distributed_execution(
            workflow=workflow,
            execution_id=execution_id,
        )

        assert isinstance(
            recovered,
            WorkflowExecution,
        )

        assert recovered is not None
        assert recovered.execution_id == execution_id
        assert recovered.status == WorkflowStatus.RUNNING

        assert recovered.step_statuses == {
            "research": StepStatus.COMPLETED,
            "analysis": StepStatus.COMPLETED,
            "report": StepStatus.RUNNING,
        }

        assert recovered.step_results == {
            "research": {
                "findings": [
                    "AI orchestration",
                    "distributed workers",
                ]
            },
            "analysis": {
                "analysis": "Analyzed 2 findings.",
            },
        }

        assert recovered.get_completed_steps() == {
            "research",
            "analysis",
        }

def test_recovery_service_reconstructs_paused_distributed_execution():
    from app.models.database import ExecutionModel
    from app.services.postgres_execution_repository import (
        PostgresExecutionRepository,
    )
    from app.services.execution_recovery_service import (
        ExecutionRecoveryService,
    )
    from app.workflows.execution import WorkflowExecution
    from app.workflows.examples import create_research_workflow
    from app.workflows.workflow_state import (
        StepStatus,
        WorkflowStatus,
    )

    workflow = create_research_workflow()

    execution = WorkflowExecution(workflow)

    execution.mark_step_running("research")
    execution.pause()

    assert execution.status == WorkflowStatus.PAUSED

    repository = PostgresExecutionRepository(SessionLocal)
    repository.save(execution)

    service = ExecutionRecoveryService(
        execution_repository=repository,
    )

    recovered = service.recover_distributed_execution(
        workflow=workflow,
        execution_id=execution.execution_id,
    )

    assert recovered is not None
    assert recovered.status == WorkflowStatus.PAUSED
    assert recovered.step_statuses["research"] == StepStatus.RUNNING

def test_recovery_service_reconstructs_paused_distributed_execution():
    from app.workflows.execution import WorkflowExecution
    from app.workflows.examples import create_research_workflow
    from app.workflows.workflow_state import (
        StepStatus,
        WorkflowStatus,
    )

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

    workflow = create_research_workflow()
    execution = WorkflowExecution(workflow)

    execution.mark_step_running("research")
    execution.pause()

    assert execution.status == WorkflowStatus.PAUSED

    repository = PostgresExecutionRepository(
        SessionLocal
    )

    repository.save(execution)

    service = ExecutionRecoveryService(
        execution_repository=repository,
    )

    recovered = service.recover_distributed_execution(
        workflow=workflow,
        execution_id=execution.execution_id,
    )

    assert recovered is not None
    assert recovered.status == WorkflowStatus.PAUSED
    assert recovered.step_statuses["research"] == (
        StepStatus.RUNNING
    )