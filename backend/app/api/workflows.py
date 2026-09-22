from fastapi import APIRouter, Depends, HTTPException

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
from app.services.security_audit_repository import (
    SecurityAuditRepository,
)
from app.models.execution_trace import (
    ExecutionTraceResponse,
)
from app.services.execution_trace_service import (
    ExecutionTraceService,
)
from app.services.security_audit_service import (
    SecurityAuditService,
)
from app.security.protected_api import require_scope_with_rate_limit
from app.security.scopes import APIScope

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)

runtime = AgentGridRuntime()

security_audit_service = SecurityAuditService(
    SecurityAuditRepository(SessionLocal)
)


@router.get(
    "",
    response_model=WorkflowListResponse,
)
def list_workflows(
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.WORKERS_READ
        )
    ),
):
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
def execute_workflow(
    workflow_name: str,
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.WORKFLOWS_EXECUTE
        )
    ),
):
    try:
        execution = runtime.execute_workflow(
            workflow_name
        )
    except KeyError:
        security_audit_service.record_event(
            key_id=api_key.key_id,
            action="workflow.execute",
            resource=workflow_name,
            endpoint=(
                "POST "
                "/workflows/{workflow_name}/execute"
            ),
            outcome="not_found"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found.",
        )

    security_audit_service.record_event(
        key_id=api_key.key_id,
        action="workflow.execute",
        resource=workflow_name,
        endpoint=(
            "POST "
            "/workflows/{workflow_name}/execute"
        ),
        outcome="allowed",
        metadata={
            "execution_id": execution.execution_id,
        },
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
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.WORKFLOWS_EXECUTE
        )
    ),    
):
    try:
        execution = runtime.execute_workflow_distributed(
            workflow_name=workflow_name,
            inputs=request.inputs,
        )
    except KeyError:
        security_audit_service.record_event(
            key_id=api_key.key_id,
            action="workflow.execute.distributed",
            resource=workflow_name,
            endpoint=(
                "POST "
                "/workflows/{workflow_name}/execute/distributed"
            ),
            outcome="not_found",
        )
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found.",
        )

    security_audit_service.record_event(
        key_id=api_key.key_id,
        action="workflow.execute.distributed",
        resource=workflow_name,
        endpoint=(
            "POST "
            "/workflows/{workflow_name}/execute/distributed"
        ),
        outcome="allowed",
        metadata={
            "execution_id": execution.execution_id,
        },
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
def get_execution(
    execution_id: str,
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_READ
        )
    ),    
):
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
def pause_execution(
    execution_id: str,
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_CONTROL
        )
    ),
):
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
def resume_execution(
    execution_id: str,
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_CONTROL
        )
    ),    
):
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
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_READ
        )
    ),
):
    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(
            session
        )

        events = repository.list_by_execution_id(
            execution_id
        )

        if event_type is not None:
            events = [
                event
                for event in events
                if event.event_type == event_type
            ]

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

@router.get(
    "/executions/{execution_id}/trace",
    response_model=ExecutionTraceResponse,
)
def get_execution_trace(
    execution_id: str,
    api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_READ
        )
    ),
):
    session = SessionLocal()

    try:
        repository = ExecutionEventRepository(
            session
        )

        service = ExecutionTraceService(
            repository
        )

        return service.get_trace(
            execution_id
        )

    finally:
        session.close()