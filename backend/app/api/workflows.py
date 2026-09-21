from fastapi import APIRouter, HTTPException

from app.core.database import SessionLocal
from app.models.execution import (
    ExecutionEventRecord,
    ExecutionEventResponse,
)
from app.models.workflow_api import (
    WorkflowExecutionDetailResponse,
    WorkflowExecutionRequest,
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


@router.get(
    "",
    response_model=WorkflowListResponse,
)
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


@router.post(
    "/{workflow_name}/execute/distributed",
    response_model=WorkflowExecutionResponse,
)
def execute_workflow_distributed(
    workflow_name: str,
    request: WorkflowExecutionRequest,
):
    try:
        execution = runtime.execute_workflow_distributed(
            workflow_name=workflow_name,
            inputs=request.inputs,
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
    execution = runtime.get_execution(
        execution_id
    )

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


@router.post(
    "/executions/{execution_id}/pause",
    response_model=WorkflowExecutionDetailResponse,
)
def pause_execution(execution_id: str):
    try:
        execution = runtime.pause_execution(
            execution_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

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


@router.post(
    "/executions/{execution_id}/resume",
    response_model=WorkflowExecutionDetailResponse,
)
def resume_execution(execution_id: str):
    try:
        execution = runtime.resume_execution(
            execution_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

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
def get_execution_events(
    execution_id: str,
    event_type: str | None = None,
):
    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(
            session
        )

        if event_type is None:
            events = repository.list_by_task(
                execution_id
            )
        else:
            events = repository.list_by_task_and_type(
                execution_id,
                event_type,
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