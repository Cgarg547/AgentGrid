from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.execution_event import ExecutionEvent
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.workers.events import WorkerEvent


def test_execution_event_repository_round_trip():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(session)

        event = WorkerEvent.create(
            event_type="task_completed",
            task_id="repository-test-1",
            data={
                "attempt": 1,
                "agent_name": "researcher",
            },
        )

        saved = repository.save(event)

        assert saved.id is not None
        assert saved.task_id == "repository-test-1"
        assert saved.event_type == "task_completed"

        events = repository.list_by_task(
            "repository-test-1"
        )

        assert len(events) == 1
        assert events[0].task_id == "repository-test-1"
        assert events[0].event_type == "task_completed"
        assert '"attempt": 1' in events[0].data

        data = ExecutionEventRepository.deserialize_data(
            events[0].data
        )

        assert data["attempt"] == 1
        assert data["agent_name"] == "researcher"

    finally:
        session.close()
        engine.dispose()


def test_execution_event_repository_filters_by_event_type():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(session)

        task_id = "repository-filter-test"

        repository.save(
            WorkerEvent.create(
                event_type="task_started",
                task_id=task_id,
                data={
                    "step_name": "research",
                },
            )
        )

        repository.save(
            WorkerEvent.create(
                event_type="task_completed",
                task_id=task_id,
                data={
                    "step_name": "research",
                },
            )
        )

        repository.save(
            WorkerEvent.create(
                event_type="task_failed",
                task_id=task_id,
                data={
                    "step_name": "analysis",
                },
            )
        )

        completed_events = (
            repository.list_by_task_and_type(
                task_id,
                "task_completed",
            )
        )

        assert len(completed_events) == 1
        assert (
            completed_events[0].event_type
            == "task_completed"
        )

        failed_events = (
            repository.list_by_task_and_type(
                task_id,
                "task_failed",
            )
        )

        assert len(failed_events) == 1
        assert (
            failed_events[0].event_type
            == "task_failed"
        )

        started_events = (
            repository.list_by_task_and_type(
                task_id,
                "task_started",
            )
        )

        assert len(started_events) == 1
        assert (
            started_events[0].event_type
            == "task_started"
        )

    finally:
        session.close()
        engine.dispose()

def test_execution_event_repository_lists_distinct_task_ids():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(session)

        repository.save(
            WorkerEvent.create(
                event_type="workflow.started",
                task_id="execution-b",
                data={},
            )
        )

        repository.save(
            WorkerEvent.create(
                event_type="step.completed",
                task_id="execution-a",
                data={},
            )
        )

        repository.save(
            WorkerEvent.create(
                event_type="workflow.completed",
                task_id="execution-b",
                data={},
            )
        )

        task_ids = repository.list_task_ids()

        assert task_ids == [
            "execution-a",
            "execution-b",
        ]

    finally:
        session.close()
        engine.dispose()