import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.database import Base
from app.models.execution_event import ExecutionEvent
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.worker import Worker


def test_worker_persists_events_to_postgres():
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = SessionLocal()

    task_id = f"event-persistence-{uuid.uuid4()}"

    queue = TaskQueue(
        f"test-worker-persistence-{uuid.uuid4()}"
    )

    worker = Worker(
        queue=queue,
        agent_handlers={
            "researcher": lambda **kwargs: {
                "message": "persisted"
            }
        },
        idempotency_store=IdempotencyStore(
            key_prefix=f"test-worker-persistence:{uuid.uuid4()}"
        ),
        event_repository=ExecutionEventRepository(
            session
        ),
    )

    try:
        Base.metadata.create_all(bind=engine)

        queue.enqueue(
            {
                "task_id": task_id,
                "step_name": "research",
                "agent_name": "researcher",
                "inputs": {},
            }
        )

        result = worker.process_one()

        assert result is not None
        assert result["status"] == "completed"

        events = (
            session.query(ExecutionEvent)
            .filter(
                ExecutionEvent.task_id == task_id
            )
            .order_by(
                ExecutionEvent.id.asc()
            )
            .all()
        )

        event_types = [
            event.event_type
            for event in events
        ]

        assert event_types == [
            "task_received",
            "task_claimed",
            "task_started",
            "task_completed",
        ]

        assert len(events) == 4

    finally:
        session.query(ExecutionEvent).filter(
            ExecutionEvent.task_id == task_id
        ).delete()

        session.commit()
        session.close()
        engine.dispose()