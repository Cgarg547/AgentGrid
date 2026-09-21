import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import SessionLocal
from app.graph.execution import LangGraphExecutionAdapter
from app.main import app
from app.models.database import Base
from app.models.execution_event import ExecutionEvent
from app.runtime import AgentGridRuntime
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.workflows.examples import create_research_workflow
from app.workflows.registry import WorkflowRegistry
from app.workflows.workflow import Workflow
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
            cleanup_session.query(
                ExecutionEvent
            ).filter(
                ExecutionEvent.task_id == task_id
            ).delete()

            cleanup_session.commit()
        finally:
            cleanup_session.close()

        engine.dispose()


def test_get_execution_events_from_langgraph_execution():
    runtime = AgentGridRuntime()

    workflow = create_research_workflow()

    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(
            session
        )

        adapter = LangGraphExecutionAdapter(
            runtime=runtime,
            event_repository=repository,
        )

        execution = adapter.execute(
            workflow,
            {
                "input": "Research AI orchestration",
            },
        )

        response = client.get(
            f"/workflows/executions/"
            f"{execution.execution_id}/events"
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["task_id"] == (
            execution.execution_id
        )

        event_types = [
            event["event_type"]
            for event in payload["events"]
        ]

        assert event_types == [
            "workflow.started",
            "step.started",
            "step.completed",
            "step.started",
            "step.completed",
            "step.started",
            "step.completed",
            "workflow.completed",
        ]

        assert len(payload["events"]) == 8

        assert payload["events"][0]["data"][
            "workflow_name"
        ] == workflow.name

        assert "started_at" in (
            payload["events"][0]["data"]
        )

        assert payload["events"][-1]["data"][
            "workflow_name"
        ] == workflow.name

        assert payload["events"][-1]["data"][
            "status"
        ] == "completed"

        assert "completed_at" in (
            payload["events"][-1]["data"]
        )

        assert "duration_ms" in (
            payload["events"][-1]["data"]
        )

        assert payload["events"][-1]["data"][
            "duration_ms"
        ] >= 0

    finally:
        session.close()


def test_get_execution_events_filtered_by_event_type():
    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(
            session
        )

        runtime = AgentGridRuntime()

        workflow = create_research_workflow()

        adapter = LangGraphExecutionAdapter(
            runtime=runtime,
            event_repository=repository,
        )

        execution = adapter.execute(
            workflow=workflow,
            inputs={
                "input": (
                    "Research distributed AI systems."
                )
            },
        )

        response = client.get(
            (
                f"/workflows/executions/"
                f"{execution.execution_id}/events"
                f"?event_type=step.completed"
            )
        )

        assert response.status_code == 200

        body = response.json()

        assert body["task_id"] == (
            execution.execution_id
        )

        assert len(body["events"]) == 3

        assert [
            event["event_type"]
            for event in body["events"]
        ] == [
            "step.completed",
            "step.completed",
            "step.completed",
        ]

        assert [
            event["data"]["step_name"]
            for event in body["events"]
        ] == [
            "research",
            "analysis",
            "report",
        ]

    finally:
        session.close()


def test_execute_workflow_api_persists_langgraph_events():
    workflow_name = "research-pipeline"

    response = client.post(
        f"/workflows/{workflow_name}/execute"
    )

    assert response.status_code == 200

    body = response.json()

    execution_id = body["execution_id"]

    events_response = client.get(
        f"/workflows/executions/"
        f"{execution_id}/events"
    )

    assert events_response.status_code == 200

    events = events_response.json()["events"]

    event_types = [
        event["event_type"]
        for event in events
    ]

    assert event_types == [
        "workflow.started",
        "step.started",
        "step.completed",
        "step.started",
        "step.completed",
        "step.started",
        "step.completed",
        "workflow.completed",
    ]


def test_execution_events_include_timing_metadata():
    response = client.post(
        "/workflows/research-pipeline/execute"
    )

    assert response.status_code == 200

    execution_id = response.json()["execution_id"]

    events_response = client.get(
        f"/workflows/executions/"
        f"{execution_id}/events"
    )

    assert events_response.status_code == 200

    events = events_response.json()["events"]

    assert len(events) == 8

    workflow_started = events[0]
    workflow_completed = events[-1]

    assert workflow_started["event_type"] == (
        "workflow.started"
    )

    assert workflow_completed["event_type"] == (
        "workflow.completed"
    )

    assert "started_at" in (
        workflow_started["data"]
    )

    assert "completed_at" in (
        workflow_completed["data"]
    )

    step_completed_events = [
        event
        for event in events
        if event["event_type"]
        == "step.completed"
    ]

    assert len(step_completed_events) == 3

    for event in step_completed_events:
        assert "duration_ms" in event["data"]

        assert isinstance(
            event["data"]["duration_ms"],
            (int, float),
        )

        assert event["data"]["duration_ms"] > 0