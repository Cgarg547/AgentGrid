from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class WorkerEvent:
    event_type: str
    task_id: str
    timestamp: datetime
    data: dict[str, Any]
    execution_id: str | None = None

    @classmethod
    def create(
        cls,
        event_type: str,
        task_id: str,
        data: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> "WorkerEvent":
        return cls(
            event_type=event_type,
            task_id=task_id,
            timestamp=datetime.now(timezone.utc),
            data=data or {},
            execution_id=execution_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "execution_id": self.execution_id,
        }