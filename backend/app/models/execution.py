from typing import Any

from pydantic import BaseModel


class ExecutionRecord(BaseModel):
    execution_id: str
    workflow_name: str
    status: str
    step_statuses: dict[str, str]
    step_results: dict[str, Any]