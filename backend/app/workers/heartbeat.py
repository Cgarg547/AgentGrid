import json
import time
from typing import Any
from uuid import uuid4

from app.core.redis import redis_client


class WorkerHeartbeatRegistry:
    def __init__(
        self,
        key_prefix: str = "agentgrid:workers",
        heartbeat_ttl_seconds: int = 30,
    ):
        if heartbeat_ttl_seconds <= 0:
            raise ValueError(
                "Heartbeat TTL must be greater than 0."
            )

        self.key_prefix = key_prefix
        self.heartbeat_ttl_seconds = heartbeat_ttl_seconds

    def _build_key(self, worker_id: str) -> str:
        return f"{self.key_prefix}:{worker_id}"

    def register(
        self,
        worker_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        worker_id = worker_id or f"worker-{uuid4()}"

        record = {
            "worker_id": worker_id,
            "status": "alive",
            "state": "idle",
            "last_heartbeat": time.time(),
            "metadata": metadata or {},
        }

        redis_client.set(
            self._build_key(worker_id),
            json.dumps(record),
            ex=self.heartbeat_ttl_seconds,
        )

        return worker_id

    def heartbeat(
        self,
        worker_id: str,
        metadata: dict[str, Any] | None = None,
        state: str | None = None,
    ) -> bool:
        key = self._build_key(worker_id)

        value = redis_client.get(key)

        if value is None:
            return False

        record = json.loads(value)

        if record.get("worker_id") != worker_id:
            return False

        record["status"] = "alive"
        record["last_heartbeat"] = time.time()

        if state is not None:
            record["state"] = state

        if metadata is not None:
            record["metadata"] = metadata

        return bool(
            redis_client.set(
                key,
                json.dumps(record),
                ex=self.heartbeat_ttl_seconds,
            )
        )

    def set_state(
        self,
        worker_id: str,
        state: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        key = self._build_key(worker_id)

        value = redis_client.get(key)

        if value is None:
            return False

        record = json.loads(value)

        if record.get("worker_id") != worker_id:
            return False

        record["state"] = state
        record["status"] = "alive"
        record["last_heartbeat"] = time.time()

        if metadata is not None:
            record["metadata"] = metadata

        return bool(
            redis_client.set(
                key,
                json.dumps(record),
                ex=self.heartbeat_ttl_seconds,
            )
        )

    def get(
        self,
        worker_id: str,
    ) -> dict[str, Any] | None:
        value = redis_client.get(
            self._build_key(worker_id)
        )

        if value is None:
            return None

        return json.loads(value)

    def is_alive(
        self,
        worker_id: str,
    ) -> bool:
        return self.get(worker_id) is not None

    def list_workers(self) -> list[dict[str, Any]]:
        pattern = f"{self.key_prefix}:*"

        workers: list[dict[str, Any]] = []

        for key in redis_client.scan_iter(
            match=pattern
        ):
            value = redis_client.get(key)

            if value is None:
                continue

            record = json.loads(value)

            workers.append(record)

        workers.sort(
            key=lambda worker: worker["worker_id"]
        )

        return workers

    def count_workers(self) -> int:
        return len(self.list_workers())

    def unregister(
        self,
        worker_id: str,
    ) -> bool:
        return bool(
            redis_client.delete(
                self._build_key(worker_id)
            )
        )
