import json
from typing import Any

from app.core.redis import redis_client


class IdempotencyStore:
    CLAIMED_STATUS = "claimed"
    COMPLETED_STATUS = "completed"

    def __init__(
        self,
        key_prefix: str = "agentgrid:idempotency",
        claim_ttl_seconds: int = 60,
    ):
        if claim_ttl_seconds <= 0:
            raise ValueError(
                "Claim TTL must be greater than 0."
            )

        self.key_prefix = key_prefix
        self.claim_ttl_seconds = claim_ttl_seconds

    def _build_key(self, task_id: str) -> str:
        return f"{self.key_prefix}:{task_id}"

    def get(self, task_id: str) -> dict[str, Any] | None:
        value = redis_client.get(
            self._build_key(task_id)
        )

        if value is None:
            return None

        return json.loads(value)

    def set(
        self,
        task_id: str,
        result: dict[str, Any],
    ) -> None:
        redis_client.set(
            self._build_key(task_id),
            json.dumps({
                "status": self.COMPLETED_STATUS,
                "result": result,
            }),
        )

    def claim(
        self,
        task_id: str,
        owner_id: str | None = None,
    ) -> bool:
        record = {
            "status": self.CLAIMED_STATUS,
        }

        if owner_id is not None:
            record["owner_id"] = owner_id

        return bool(
            redis_client.set(
                self._build_key(task_id),
                json.dumps(record),
                nx=True,
                ex=self.claim_ttl_seconds,
            )
        )

    def renew_claim(
        self,
        task_id: str,
        owner_id: str | None = None,
    ) -> bool:
        key = self._build_key(task_id)

        if owner_id is None:
            value = redis_client.get(key)

            if value is None:
                return False

            record = json.loads(value)

            if record.get("status") != self.CLAIMED_STATUS:
                return False

            return bool(
                redis_client.expire(
                    key,
                    self.claim_ttl_seconds,
                )
            )

        script = """
        local value = redis.call('GET', KEYS[1])

        if not value then
            return 0
        end

        local record = cjson.decode(value)

        if record['status'] ~= ARGV[1] then
            return 0
        end

        if record['owner_id'] ~= ARGV[2] then
            return 0
        end

        redis.call('EXPIRE', KEYS[1], ARGV[3])

        return 1
        """

        result = redis_client.eval(
            script,
            1,
            key,
            self.CLAIMED_STATUS,
            owner_id,
            self.claim_ttl_seconds,
        )

        return bool(result)


    def delete(
        self,
        task_id: str,
        owner_id: str | None = None,
    ) -> bool:
        key = self._build_key(task_id)

        if owner_id is None:
            return bool(
                redis_client.delete(key)
            )

        script = """
        local value = redis.call('GET', KEYS[1])

        if not value then
            return 0
        end

        local record = cjson.decode(value)

        if record['status'] ~= ARGV[1] then
            return 0
        end

        if record['owner_id'] ~= ARGV[2] then
            return 0
        end

        redis.call('DEL', KEYS[1])

        return 1
        """

        result = redis_client.eval(
            script,
            1,
            key,
            self.CLAIMED_STATUS,
            owner_id,
        )

        return bool(result)