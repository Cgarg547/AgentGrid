from fastapi import APIRouter, HTTPException

from app.core.database import SessionLocal
from app.models.execution import (
    ExecutionEventRecord,
    ExecutionEventResponse,
)
from app.models.workflow_api import (
    WorkflowExecutionDetailResponse,
    WorkflowExecutionResponse,
    WorkflowListResponse,
)
from app.runtime import AgentGridRuntime
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)


router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)


runtime = AgentGridRuntime()


@router.get("", response_model=WorkflowListResponse)
def list_workflows():
    return {
        "workflows": [
            workflow.describe()
            for workflow in runtime.workflow_registry.list()
        ]
    }


@router.post(
    "/{workflow_name}/execute",
    response_model=WorkflowExecutionResponse,
)
def execute_workflow(workflow_name: str):
    try:
        execution = runtime.execute_workflow(
            workflow_name
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found.",
        )

    return {
        "execution_id": execution.execution_id,
        "workflow": workflow_name,
        "status": execution.status.value,
        "step_results": execution.step_results,
    }


@router.get(
    "/executions/{execution_id}",
    response_model=WorkflowExecutionDetailResponse,
)
def get_execution(execution_id: str):
    execution = runtime.get_execution(execution_id)

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail=f"Execution '{execution_id}' not found.",
        )

    return {
        "execution_id": execution.execution_id,
        "workflow": execution.workflow.name,
        "status": execution.status.value,
        "step_statuses": {
            name: status.value
            for name, status in execution.step_statuses.items()
        },
        "step_results": execution.step_results,
    }


@router.get(
    "/executions/{execution_id}/events",
    response_model=ExecutionEventResponse,
)
def get_execution_events(execution_id: str):
    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(session)

        events = repository.list_by_task(
            execution_id
        )

        return {
            "task_id": execution_id,
            "events": [
                ExecutionEventRecord(
                    id=event.id,
                    task_id=event.task_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    data=ExecutionEventRepository.deserialize_data(
                        event.data
                    ),
                )
                for event in events
            ],
        }
    finally:
        session.close()