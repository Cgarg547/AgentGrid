from typing import Any

from pydantic import BaseModel


class WorkflowListResponse(BaseModel):
    workflows: list[dict[str, Any]]


class WorkflowExecutionRequest(BaseModel):
    inputs: dict[str, Any] = {}


class WorkflowExecutionResponse(BaseModel):
    execution_id: str
    workflow: str
    status: str
    step_results: dict[str, Any]


class WorkflowExecutionDetailResponse(BaseModel):
    execution_id: str
    workflow: str
    status: str
    step_statuses: dict[str, str]
    step_results: dict[str, Any]