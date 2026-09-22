import logging

from fastapi import FastAPI
from app.api.approvals import router as approval_router
from app.api.workflows import router as workflow_router
from app.api.workers import router as worker_router
from app.core.config import settings
from app.core.logging import setup_logging


setup_logging()

logger = logging.getLogger("agentgrid")


app = FastAPI(
    title=settings.app_name,
    description="Distributed AI Agent Orchestration Platform",
    version=settings.app_version,
)

app.include_router(workflow_router)
app.include_router(approval_router)
app.include_router(worker_router)


@app.get("/")
def root():
    logger.info("Root endpoint accessed")

    return {
        "name": settings.app_name,
        "status": "running",
        "version": settings.app_version,
        "environment": settings.app_environment,
    }


@app.get("/health")
def health():
    logger.info("Health check requested")

    return {
        "status": "healthy",
    }