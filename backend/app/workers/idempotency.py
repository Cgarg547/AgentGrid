import json
from typing import Any

from app.core.redis import redis_client


class IdempotencyStore:
    CLAIMED_STATUS = "claimed"
    COMPLETED_STATUS = "completed"

    def __init__(self, key_prefix: str = "agentgrid:idempotency"):
        self.key_prefix = key_prefix

    def _build_key(self, task_id: str) -> str:
        return f"{self.key_prefix}:{task_id}"

    def get(self, task_id: str) -> dict[str, Any] | None:
        value = redis_client.get(self._build_key(task_id))

        if value is None:
            return None

        return json.loads(value)

    def set(self, task_id: str, result: dict[str, Any]) -> None:
        redis_client.set(
            self._build_key(task_id),
            json.dumps({
                "status": self.COMPLETED_STATUS,
                "result": result,
            }),
        )

    def claim(self, task_id: str) -> bool:
        return bool(
            redis_client.set(
                self._build_key(task_id),
                json.dumps({
                    "status": self.CLAIMED_STATUS,
                }),
                nx=True,
            )
        )

    def delete(self, task_id: str) -> None:
        redis_client.delete(self._build_key(task_id))