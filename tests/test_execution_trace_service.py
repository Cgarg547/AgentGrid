from datetime import datetime, timezone

from app.models.execution_event import ExecutionEvent
from app.services.execution_trace_service import (
    ExecutionTraceService,
)


class FakeExecutionEventRepository:
    def __init__(self, events):
        self.events = events

    def list_by_execution_id(self, execution_id):
        return [
            event
            for event in self.events
            if event.execution_id == execution_id
        ]


def make_event(
    event_id,
    execution_id,
    task_id,
    event_type,
    data,
):
    return ExecutionEvent(
        id=event_id,
        execution_id=execution_id,
        task_id=task_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        data=data,
    )


def test_trace_groups_events_by_task():
    execution_id = "execution-123"

    events = [
        make_event(
            1,
            execution_id,
            "task-1",
            "task_received",
            '{"step_name": "research"}',
        ),
        make_event(
            2,
            execution_id,
            "task-1",
            "task_started",
            '{"attempt": 1}',
        ),
        make_event(
            3,
            execution_id,
            "task-1",
            "task_completed",
            '{"attempt": 1}',
        ),
        make_event(
            4,
            execution_id,
            "task-2",
            "task_received",
            '{"step_name": "analysis"}',
        ),
    ]

    repository = FakeExecutionEventRepository(events)
    service = ExecutionTraceService(repository)

    trace = service.get_trace(execution_id)

    assert trace["execution_id"] == execution_id
    assert len(trace["tasks"]) == 2

    first_task = trace["tasks"][0]

    assert first_task["task_id"] == "task-1"
    assert [
        event["event_type"]
        for event in first_task["events"]
    ] == [
        "task_received",
        "task_started",
        "task_completed",
    ]

    assert first_task["events"][0]["data"] == {
        "step_name": "research"
    }


def test_trace_returns_empty_tasks_when_no_events_exist():
    execution_id = "execution-empty"

    repository = FakeExecutionEventRepository([])
    service = ExecutionTraceService(repository)

    trace = service.get_trace(execution_id)

    assert trace == {
        "execution_id": execution_id,
        "tasks": [],
    }