from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ExecutionRecord(BaseModel):
    execution_id: str
    workflow_name: str
    status: str
    step_statuses: dict[str, str]
    step_results: dict[str, Any]


class ExecutionEventRecord(BaseModel):
    id: int
    task_id: str
    event_type: str
    timestamp: datetime
    data: dict[str, Any]


class ExecutionEventResponse(BaseModel):
    task_id: str
    events: list[ExecutionEventRecord]