from fastapi import APIRouter, HTTPException

from app.models.workflow_schedule_api import (
    WorkflowScheduleCreateRequest,
    WorkflowScheduleListResponse,
    WorkflowScheduleResponse,
)
from app.runtime import AgentGridRuntime


router = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
)


runtime = AgentGridRuntime()
schedule_service = runtime.workflow_schedule_service


def _to_response(schedule) -> WorkflowScheduleResponse:
    return WorkflowScheduleResponse(
        schedule_id=schedule.schedule_id,
        workflow_name=schedule.workflow_name,
        next_run_at=schedule.next_run_at,
        enabled=schedule.enabled,
        created_at=schedule.created_at,
    )


@router.post(
    "",
    response_model=WorkflowScheduleResponse,
)
def create_schedule(
    request: WorkflowScheduleCreateRequest,
):
    try:
        runtime.workflow_registry.get(request.workflow_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{request.workflow_name}' not found.",
        )

    schedule = schedule_service.create_schedule(
        workflow_name=request.workflow_name,
        next_run_at=request.next_run_at,
    )

    return _to_response(schedule)


@router.get(
    "",
    response_model=WorkflowScheduleListResponse,
)
def list_schedules(
    enabled: bool | None = None,
):
    schedules = schedule_service.list_schedules(
        enabled=enabled,
    )

    return {
        "schedules": [
            _to_response(schedule)
            for schedule in schedules
        ],
        "count": len(schedules),
    }


@router.get(
    "/{schedule_id}",
    response_model=WorkflowScheduleResponse,
)
def get_schedule(schedule_id: str):
    schedule = schedule_service.get_schedule(schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail=f"Schedule '{schedule_id}' not found.",
        )

    return _to_response(schedule)


@router.post(
    "/{schedule_id}/enable",
    response_model=WorkflowScheduleResponse,
)
def enable_schedule(schedule_id: str):
    updated = schedule_service.enable_schedule(schedule_id)

    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Schedule '{schedule_id}' not found.",
        )

    schedule = schedule_service.get_schedule(schedule_id)

    return _to_response(schedule)


@router.post(
    "/{schedule_id}/disable",
    response_model=WorkflowScheduleResponse,
)
def disable_schedule(schedule_id: str):
    updated = schedule_service.disable_schedule(schedule_id)

    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Schedule '{schedule_id}' not found.",
        )

    schedule = schedule_service.get_schedule(schedule_id)

    return _to_response(schedule)


@router.delete(
    "/{schedule_id}",
)
def delete_schedule(schedule_id: str):
    deleted = schedule_service.delete_schedule(
        schedule_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Schedule '{schedule_id}' not found.",
        )

    return {
        "schedule_id": schedule_id,
        "deleted": True,
    }