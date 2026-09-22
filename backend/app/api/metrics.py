from fastapi import APIRouter, Depends

from app.workers.metrics import WorkerMetrics


router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
)


worker_metrics = WorkerMetrics()


def get_worker_metrics() -> WorkerMetrics:
    return worker_metrics


@router.get("/queues")
def get_queue_metrics(
    metrics: WorkerMetrics = Depends(get_worker_metrics),
):
    return metrics.queue_metrics()


@router.get("/workers")
def get_worker_metrics_status(
    metrics: WorkerMetrics = Depends(get_worker_metrics),
):
    return metrics.worker_metrics()


@router.get("")
def get_metrics(
    metrics: WorkerMetrics = Depends(get_worker_metrics),
):
    return metrics.snapshot()