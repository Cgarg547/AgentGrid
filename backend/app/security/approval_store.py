import json

from app.core.redis import redis_client
from app.security.approval import (
    ApprovalRequest,
    ApprovalStatus,
)


class ApprovalStore:
    def __init__(
        self,
        key_prefix: str = "agentgrid:approval",
    ):
        self.key_prefix = key_prefix

    def _build_key(
        self,
        request_id: str,
    ) -> str:
        return f"{self.key_prefix}:{request_id}"

    def save(
        self,
        request: ApprovalRequest,
    ) -> None:
        redis_client.set(
            self._build_key(request.request_id),
            json.dumps(request.describe()),
        )

    def get(
        self,
        request_id: str,
    ) -> ApprovalRequest | None:
        value = redis_client.get(
            self._build_key(request_id)
        )

        if value is None:
            return None

        data = json.loads(value)

        return ApprovalRequest(
            request_id=data["request_id"],
            agent_name=data["agent_name"],
            tool_name=data["tool_name"],
            arguments=data.get("arguments", {}),
            status=ApprovalStatus(data["status"]),
        )

    def delete(
        self,
        request_id: str,
    ) -> None:
        redis_client.delete(
            self._build_key(request_id)
        )

    def approve(
        self,
        request_id: str,
    ) -> ApprovalRequest:
        request = self.get(request_id)

        if request is None:
            raise KeyError(
                f"Approval request '{request_id}' not found."
            )

        request.approve()
        self.save(request)

        return request

    def reject(
        self,
        request_id: str,
    ) -> ApprovalRequest:
        request = self.get(request_id)

        if request is None:
            raise KeyError(
                f"Approval request '{request_id}' not found."
            )

        request.reject()
        self.save(request)

        return request