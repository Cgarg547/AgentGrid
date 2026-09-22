from datetime import datetime

from pydantic import BaseModel


class ExecutionTraceEvent(BaseModel):
    id: int
    task_id: str
    event_type: str
    timestamp: datetime
    data: dict


class ExecutionTraceTask(BaseModel):
    task_id: str
    events: list[ExecutionTraceEvent]


class ExecutionTraceResponse(BaseModel):
    execution_id: str
    tasks: list[ExecutionTraceTask]