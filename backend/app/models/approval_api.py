from typing import Any

from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    request_id: str
    agent_name: str
    tool_name: str
    status: str


class ApprovalExecutionResponse(BaseModel):
    request_id: str
    agent_name: str
    tool_name: str
    status: str
    execution_result: dict[str, Any]