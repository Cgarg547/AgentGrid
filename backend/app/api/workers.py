from fastapi import APIRouter, HTTPException

from app.models.worker_api import (
    WorkerListResponse,
    WorkerResponse,
)
from app.workers.heartbeat import WorkerHeartbeatRegistry


router = APIRouter(
    prefix="/workers",
    tags=["workers"],
)


worker_registry = WorkerHeartbeatRegistry()


@router.get(
    "",
    response_model=WorkerListResponse,
)
def list_workers():
    workers = worker_registry.list_workers()

    return {
        "workers": workers,
        "count": len(workers),
    }


@router.get(
    "/{worker_id}",
    response_model=WorkerResponse,
)
def get_worker(worker_id: str):
    worker = worker_registry.get(worker_id)

    if worker is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Worker '{worker_id}' not found."
            ),
        )

    return worker
