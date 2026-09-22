from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models.execution_event import ExecutionEvent
from app.services.execution_event_repository import (
    ExecutionEventRepository,
)


class ExecutionTraceService:
    def __init__(
        self,
        repository: ExecutionEventRepository,
    ):
        self.repository = repository

    def get_trace(
        self,
        execution_id: str,
    ) -> dict[str, Any]:
        events = self.repository.list_by_execution_id(
            execution_id
        )

        grouped_events: dict[str, list[dict[str, Any]]] = (
            defaultdict(list)
        )

        for event in events:
            grouped_events[event.task_id].append(
                {
                    "id": event.id,
                    "task_id": event.task_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "data": (
                        ExecutionEventRepository
                        .deserialize_data(event.data)
                    ),
                }
            )

        return {
            "execution_id": execution_id,
            "tasks": [
                {
                    "task_id": task_id,
                    "events": task_events,
                }
                for task_id, task_events
                in grouped_events.items()
            ],
        }