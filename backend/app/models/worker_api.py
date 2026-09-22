from typing import Any

from pydantic import BaseModel


class WorkerResponse(BaseModel):
    worker_id: str
    status: str
    state: str
    last_heartbeat: float
    metadata: dict[str, Any]


class WorkerListResponse(BaseModel):
    workers: list[WorkerResponse]
    count: int
