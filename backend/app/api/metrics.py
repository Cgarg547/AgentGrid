from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.protected_api import require_scope_with_rate_limit
from app.security.scopes import APIScope
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)
from app.services.execution_metrics import ExecutionMetrics
from app.workers.metrics import WorkerMetrics


router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
)


worker_metrics = WorkerMetrics()


def get_worker_metrics():
    return worker_metrics


def get_execution_metrics(
    db: Session = Depends(get_db),
) -> ExecutionMetrics:
    return ExecutionMetrics(
        ExecutionEventRepository(db)
    )


@router.get("/queues")
def get_queue_metrics(
    metrics: WorkerMetrics = Depends(get_worker_metrics),
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.WORKERS_READ
        )
    ),
):
    return metrics.queue_metrics()


@router.get("/workers")
def get_worker_metrics_status(
    metrics: WorkerMetrics = Depends(get_worker_metrics),
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.WORKERS_READ
        )
    ),
):
    return metrics.worker_metrics()


@router.get("/executions/summary")
def get_execution_metrics_summary(
    workflow_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    metrics: ExecutionMetrics = Depends(
        get_execution_metrics
    ),
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_READ
        )
    ),
):
    try:
        return metrics.aggregate_metrics(
            workflow_name=workflow_name,
            start_time=start_time,
            end_time=end_time,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/executions/{execution_id}")
def get_execution_metrics_status(
    execution_id: str,
    metrics: ExecutionMetrics = Depends(
        get_execution_metrics
    ),
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_READ
        )
    ),
):
    return metrics.execution_metrics(
        execution_id
    )


@router.get("/executions/{execution_id}/steps")
def get_execution_step_metrics(
    execution_id: str,
    metrics: ExecutionMetrics = Depends(
        get_execution_metrics
    ),
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.EXECUTIONS_READ
        )
    ),
):
    return {
        "execution_id": execution_id,
        "steps": metrics.step_metrics(
            execution_id
        ),
    }


@router.get("")
def get_metrics(
    metrics: WorkerMetrics = Depends(
        get_worker_metrics
    ),
    _current_api_key=Depends(
        require_scope_with_rate_limit(
            APIScope.WORKERS_READ
        )
    ),
):
    return metrics.snapshot()