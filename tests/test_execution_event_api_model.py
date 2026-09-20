from datetime import datetime, timezone

from app.models.execution import (
    ExecutionEventRecord,
    ExecutionEventResponse,
)


def test_execution_event_record():
    event = ExecutionEventRecord(
        id=1,
        task_id="task-123",
        event_type="task_completed",
        timestamp=datetime.now(timezone.utc),
        data={
            "attempt": 1,
        },
    )

    assert event.id == 1
    assert event.task_id == "task-123"
    assert event.event_type == "task_completed"
    assert event.data["attempt"] == 1


def test_execution_event_response():
    event = ExecutionEventRecord(
        id=1,
        task_id="task-123",
        event_type="task_completed",
        timestamp=datetime.now(timezone.utc),
        data={
            "attempt": 1,
        },
    )

    response = ExecutionEventResponse(
        task_id="task-123",
        events=[event],
    )

    assert response.task_id == "task-123"
    assert len(response.events) == 1
    assert response.events[0].event_type == "task_completed"