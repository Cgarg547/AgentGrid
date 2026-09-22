import json
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.metrics import (
    get_execution_metrics,
    router,
)
from app.models.execution_event import ExecutionEvent
from app.services.execution_event_repository import ExecutionEventRepository
from app.services.execution_metrics import ExecutionMetrics
from app.workers.events import WorkerEvent


class FakeExecutionEventRepository:
    def __init__(self, events):
        self.events = events

    def list_by_task(self, execution_id):
        return [
            event
            for event in self.events
            if event.task_id == execution_id
        ]

    def list_task_ids(self):
        return sorted({
            event.task_id
            for event in self.events
        })


def make_event(
    task_id,
    event_type,
    data,
    timestamp=None,
):
    return ExecutionEvent(
        id=1,
        task_id=task_id,
        event_type=event_type,
        timestamp=(
            timestamp
            if timestamp is not None
            else datetime.now(timezone.utc)
        ),
        data=json.dumps(data),
    )


def create_client(events):
    repository = FakeExecutionEventRepository(
        events
    )

    app = FastAPI()
    app.include_router(router)

    def override_execution_metrics():
        return ExecutionMetrics(repository)

    app.dependency_overrides[
        get_execution_metrics
    ] = override_execution_metrics

    return TestClient(app)


def test_execution_metrics_api_returns_execution_metrics():
    execution_id = "api-execution-1"

    client = create_client([
        make_event(
            execution_id,
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            execution_id,
            "step.completed",
            {
                "step_name": "research",
                "duration_ms": 100.0,
            },
        ),
        make_event(
            execution_id,
            "workflow.completed",
            {
                "duration_ms": 250.0,
            },
        ),
    ])

    response = client.get(
        f"/metrics/executions/{execution_id}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "execution_id": execution_id,
        "status": "completed",
        "duration_ms": 250.0,
        "step_count": 1,
    }


def test_execution_metrics_api_returns_step_metrics():
    execution_id = "api-execution-steps"

    client = create_client([
        make_event(
            execution_id,
            "step.completed",
            {
                "step_name": "research",
                "duration_ms": 100.0,
            },
        ),
        make_event(
            execution_id,
            "step.failed",
            {
                "step_name": "analysis",
                "duration_ms": 50.0,
            },
        ),
    ])

    response = client.get(
        f"/metrics/executions/{execution_id}/steps"
    )

    assert response.status_code == 200
    assert response.json() == {
        "execution_id": execution_id,
        "steps": [
            {
                "step_name": "research",
                "event_type": "step.completed",
                "duration_ms": 100.0,
            },
            {
                "step_name": "analysis",
                "event_type": "step.failed",
                "duration_ms": 50.0,
            },
        ],
    }


def test_execution_metrics_api_returns_summary():
    client = create_client([
        make_event(
            "api-summary-1",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            "api-summary-1",
            "workflow.completed",
            {
                "duration_ms": 100.0,
            },
        ),
        make_event(
            "api-summary-1",
            "step.completed",
            {
                "step_name": "research",
                "duration_ms": 50.0,
            },
        ),
        make_event(
            "api-summary-2",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            "api-summary-2",
            "workflow.completed",
            {
                "duration_ms": 200.0,
            },
        ),
        make_event(
            "api-summary-2",
            "step.completed",
            {
                "step_name": "research",
                "duration_ms": 100.0,
            },
        ),
        make_event(
            "api-summary-2",
            "step.completed",
            {
                "step_name": "analysis",
                "duration_ms": 100.0,
            },
        ),
        make_event(
            "api-summary-3",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            "api-summary-3",
            "workflow.failed",
            {
                "duration_ms": 150.0,
            },
        ),
        make_event(
            "api-summary-3",
            "step.failed",
            {
                "step_name": "analysis",
                "duration_ms": 75.0,
            },
        ),
    ])

    response = client.get(
        "/metrics/executions/summary"
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_executions": 3,
        "completed": 2,
        "failed": 1,
        "unknown": 0,
        "success_rate": 2 / 3,
        "average_duration_ms": 150.0,
        "average_step_count": 4 / 3,
    }


def test_aggregate_metrics_filters_by_workflow_name():
    events = [
        make_event(
            "execution-1",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            "execution-1",
            "workflow.completed",
            {
                "workflow_name": "research-pipeline",
                "duration_ms": 100.0,
            },
        ),
        make_event(
            "execution-2",
            "workflow.started",
            {
                "workflow_name": "email-pipeline",
            },
        ),
        make_event(
            "execution-2",
            "workflow.completed",
            {
                "workflow_name": "email-pipeline",
                "duration_ms": 200.0,
            },
        ),
    ]

    repository = FakeExecutionEventRepository(
        events
    )

    metrics = ExecutionMetrics(repository)

    result = metrics.aggregate_metrics(
        workflow_name="research-pipeline"
    )

    assert result["total_executions"] == 1
    assert result["completed"] == 1
    assert result["failed"] == 0
    assert result["unknown"] == 0
    assert result["success_rate"] == 1.0
    assert result["average_duration_ms"] == 100.0


def test_aggregate_metrics_ignores_non_workflow_task_ids():
    events = [
        make_event(
            "workflow-execution-1",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            "workflow-execution-1",
            "workflow.completed",
            {
                "workflow_name": "research-pipeline",
                "duration_ms": 100.0,
            },
        ),
        make_event(
            "worker-task-1",
            "task.started",
            {
                "worker_id": "worker-1",
            },
        ),
        make_event(
            "worker-task-1",
            "task.completed",
            {
                "worker_id": "worker-1",
                "duration_ms": 25.0,
            },
        ),
    ]

    repository = FakeExecutionEventRepository(
        events
    )

    metrics = ExecutionMetrics(repository)

    result = metrics.aggregate_metrics()

    assert result["total_executions"] == 1
    assert result["completed"] == 1
    assert result["failed"] == 0
    assert result["unknown"] == 0
    assert result["success_rate"] == 1.0
    assert result["average_duration_ms"] == 100.0

def test_aggregate_metrics_filters_by_time_window():
    start_time = datetime(
        2026,
        9,
        22,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2026,
        9,
        22,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    events = [
        make_event(
            "execution-before",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
            timestamp=datetime(
                2026,
                9,
                22,
                9,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        ),
        make_event(
            "execution-before",
            "workflow.completed",
            {
                "workflow_name": "research-pipeline",
                "duration_ms": 50.0,
            },
            timestamp=datetime(
                2026,
                9,
                22,
                9,
                1,
                0,
                tzinfo=timezone.utc,
            ),
        ),
        make_event(
            "execution-inside",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
            timestamp=datetime(
                2026,
                9,
                22,
                11,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        ),
        make_event(
            "execution-inside",
            "workflow.completed",
            {
                "workflow_name": "research-pipeline",
                "duration_ms": 100.0,
            },
            timestamp=datetime(
                2026,
                9,
                22,
                11,
                1,
                0,
                tzinfo=timezone.utc,
            ),
        ),
        make_event(
            "execution-after",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
            timestamp=datetime(
                2026,
                9,
                22,
                13,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        ),
        make_event(
            "execution-after",
            "workflow.completed",
            {
                "workflow_name": "research-pipeline",
                "duration_ms": 200.0,
            },
            timestamp=datetime(
                2026,
                9,
                22,
                13,
                1,
                0,
                tzinfo=timezone.utc,
            ),
        ),
    ]

    repository = FakeExecutionEventRepository(
        events
    )

    metrics = ExecutionMetrics(repository)

    result = metrics.aggregate_metrics(
        start_time=start_time,
        end_time=end_time,
    )

    assert result["total_executions"] == 1
    assert result["completed"] == 1
    assert result["failed"] == 0
    assert result["unknown"] == 0
    assert result["success_rate"] == 1.0
    assert result["average_duration_ms"] == 100.0