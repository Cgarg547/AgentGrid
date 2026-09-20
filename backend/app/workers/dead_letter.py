import json
from typing import Any

from app.core.redis import redis_client


class DeadLetterQueue:
    def __init__(
        self,
        queue_name: str = "agentgrid:dead-letter",
    ):
        self.queue_name = queue_name

    def enqueue(self, task: dict[str, Any]) -> None:
        redis_client.rpush(
            self.queue_name,
            json.dumps(task),
        )

    def dequeue(self) -> dict[str, Any] | None:
        value = redis_client.lpop(self.queue_name)

        if value is None:
            return None

        return json.loads(value)

    def size(self) -> int:
        return redis_client.llen(self.queue_name)

    def clear(self) -> None:
        redis_client.delete(self.queue_name)