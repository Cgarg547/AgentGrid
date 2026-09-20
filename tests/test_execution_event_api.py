import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import app
from app.models.database import Base
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.workers.idempotency import IdempotencyStore
from app.workers.queue import TaskQueue
from app.workers.worker import Worker


client = TestClient(app)


def test_get_execution_events_from_real_worker():
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

    task_id = f"api-event-{uuid.uuid4()}"

    queue = TaskQueue(
        f"test-api-events-{uuid.uuid4()}"
    )

    worker = Worker(
        queue=queue,
        agent_handlers={
            "researcher": lambda **kwargs: {
                "message": "completed"
            }
        },
        idempotency_store=IdempotencyStore(
            key_prefix=f"test-api-events:{uuid.uuid4()}"
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

        response = client.get(
            f"/workflows/executions/{task_id}/events"
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["task_id"] == task_id

        event_types = [
            event["event_type"]
            for event in payload["events"]
        ]

        assert event_types == [
            "task_received",
            "task_claimed",
            "task_started",
            "task_completed",
        ]

        assert len(payload["events"]) == 4

        assert payload["events"][0]["data"] == {
            "step_name": "research",
            "agent_name": "researcher",
        }

        assert payload["events"][3]["data"] == {
            "step_name": "research",
            "agent_name": "researcher",
            "attempt": 1,
        }

    finally:
        session.close()

        cleanup_session = SessionLocal()

        try:
            from app.models.execution_event import ExecutionEvent

            cleanup_session.query(
                ExecutionEvent
            ).filter(
                ExecutionEvent.task_id == task_id
            ).delete()

            cleanup_session.commit()
        finally:
            cleanup_session.close()

        engine.dispose()