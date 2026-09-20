from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalRequest:
    request_id: str
    agent_name: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING

    def approve(self) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(
                "Only pending approval requests can be approved."
            )

        self.status = ApprovalStatus.APPROVED

    def reject(self) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(
                "Only pending approval requests can be rejected."
            )

        self.status = ApprovalStatus.REJECTED

    def describe(self) -> dict:
        return {
            "request_id": self.request_id,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "status": self.status.value,
        }