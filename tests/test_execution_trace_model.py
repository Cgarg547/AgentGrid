from datetime import datetime, timezone

from app.models.execution_trace import (
    ExecutionTraceEvent,
    ExecutionTraceResponse,
    ExecutionTraceTask,
)


def test_execution_trace_response_model():
    timestamp = datetime.now(timezone.utc)

    event = ExecutionTraceEvent(
        id=1,
        task_id="task-1",
        event_type="task_completed",
        timestamp=timestamp,
        data={
            "step_name": "research",
            "attempt": 1,
        },
    )

    task = ExecutionTraceTask(
        task_id="task-1",
        events=[event],
    )

    response = ExecutionTraceResponse(
        execution_id="execution-123",
        tasks=[task],
    )

    assert response.execution_id == "execution-123"
    assert len(response.tasks) == 1
    assert response.tasks[0].task_id == "task-1"
    assert response.tasks[0].events[0].event_type == "task_completed"
    assert response.tasks[0].events[0].data["step_name"] == "research"


def test_execution_trace_response_supports_empty_tasks():
    response = ExecutionTraceResponse(
        execution_id="execution-empty",
        tasks=[],
    )

    assert response.execution_id == "execution-empty"
    assert response.tasks == []