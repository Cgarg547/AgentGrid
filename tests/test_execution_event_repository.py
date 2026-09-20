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
    finally:
        session.close()
        engine.dispose()