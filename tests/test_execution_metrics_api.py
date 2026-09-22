import json
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.metrics import (
    get_execution_metrics,
    router,
)
from app.core.database import SessionLocal
from app.models.execution_event import ExecutionEvent
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.services.execution_metrics import ExecutionMetrics


api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


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
):
    return ExecutionEvent(
        id=1,
        task_id=task_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
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

    test_key, raw_key = api_key_service.create_api_key(
        "execution-metrics-api-test",
        scopes=[
            "executions:read",
        ],
    )

    client = TestClient(app)

    client._agentgrid_test_key_id = test_key.key_id

    client.headers.update({
        "Authorization": f"Bearer {raw_key}"
    })

    return client


def cleanup_client(client):
    key_id = getattr(
        client,
        "_agentgrid_test_key_id",
        None,
    )

    if key_id is not None:
        api_key_service.delete_api_key(
            key_id
        )


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

    try:
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
    finally:
        cleanup_client(client)


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

    try:
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
    finally:
        cleanup_client(client)


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

    try:
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
    finally:
        cleanup_client(client)


def test_execution_metrics_summary_filters_by_workflow_name():
    client = create_client([
        make_event(
            "api-filter-1",
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            "api-filter-1",
            "workflow.completed",
            {
                "workflow_name": "research-pipeline",
                "duration_ms": 100.0,
            },
        ),
        make_event(
            "api-filter-2",
            "workflow.started",
            {
                "workflow_name": "email-pipeline",
            },
        ),
        make_event(
            "api-filter-2",
            "workflow.completed",
            {
                "workflow_name": "email-pipeline",
                "duration_ms": 200.0,
            },
        ),
    ])

    try:
        response = client.get(
            "/metrics/executions/summary",
            params={
                "workflow_name": "research-pipeline",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "total_executions": 1,
            "completed": 1,
            "failed": 0,
            "unknown": 0,
            "success_rate": 1.0,
            "average_duration_ms": 100.0,
            "average_step_count": 0.0,
        }
    finally:
        cleanup_client(client)


def test_execution_metrics_summary_filters_by_time_window():
    inside_execution = "api-time-inside"
    outside_execution = "api-time-outside"

    events = [
        make_event(
            inside_execution,
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            inside_execution,
            "workflow.completed",
            {
                "duration_ms": 100.0,
            },
        ),
        make_event(
            outside_execution,
            "workflow.started",
            {
                "workflow_name": "research-pipeline",
            },
        ),
        make_event(
            outside_execution,
            "workflow.completed",
            {
                "duration_ms": 200.0,
            },
        ),
    ]

    events[0].timestamp = datetime(
        2026,
        9,
        22,
        11,
        0,
        tzinfo=timezone.utc,
    )

    events[1].timestamp = datetime(
        2026,
        9,
        22,
        11,
        1,
        tzinfo=timezone.utc,
    )

    events[2].timestamp = datetime(
        2026,
        9,
        22,
        13,
        0,
        tzinfo=timezone.utc,
    )

    events[3].timestamp = datetime(
        2026,
        9,
        22,
        13,
        1,
        tzinfo=timezone.utc,
    )

    client = create_client(events)

    try:
        response = client.get(
            "/metrics/executions/summary",
            params={
                "start_time": "2026-09-22T10:00:00Z",
                "end_time": "2026-09-22T12:00:00Z",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "total_executions": 1,
            "completed": 1,
            "failed": 0,
            "unknown": 0,
            "success_rate": 1.0,
            "average_duration_ms": 100.0,
            "average_step_count": 0.0,
        }
    finally:
        cleanup_client(client)


def test_execution_metrics_summary_rejects_invalid_time_window():
    client = create_client([])

    try:
        response = client.get(
            "/metrics/executions/summary",
            params={
                "start_time": "2026-09-22T12:00:00Z",
                "end_time": "2026-09-22T10:00:00Z",
            },
        )

        assert response.status_code == 400
    finally:
        cleanup_client(client)