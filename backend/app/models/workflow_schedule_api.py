from datetime import datetime

from pydantic import BaseModel


class WorkflowScheduleCreateRequest(BaseModel):
    workflow_name: str
    next_run_at: datetime


class WorkflowScheduleResponse(BaseModel):
    schedule_id: str
    workflow_name: str
    next_run_at: datetime
    enabled: bool
    created_at: datetime


class WorkflowScheduleListResponse(BaseModel):
    schedules: list[WorkflowScheduleResponse]
    count: int