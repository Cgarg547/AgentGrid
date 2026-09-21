import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.execution_event import ExecutionEvent
from app.workers.events import WorkerEvent


class ExecutionEventRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(
        self,
        event: WorkerEvent,
    ) -> ExecutionEvent:
        record = ExecutionEvent(
            task_id=event.task_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            data=self._serialize_data(
                event.data
            ),
        )

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        return record

    def list_by_task(
        self,
        task_id: str,
    ) -> list[ExecutionEvent]:
        return (
            self.session.query(ExecutionEvent)
            .filter(
                ExecutionEvent.task_id == task_id
            )
            .order_by(
                ExecutionEvent.timestamp.asc()
            )
            .all()
        )

    def list_by_task_and_type(
        self,
        task_id: str,
        event_type: str,
    ) -> list[ExecutionEvent]:
        return (
            self.session.query(ExecutionEvent)
            .filter(
                ExecutionEvent.task_id == task_id,
                ExecutionEvent.event_type == event_type,
            )
            .order_by(
                ExecutionEvent.timestamp.asc()
            )
            .all()
        )

    @staticmethod
    def _serialize_data(
        data: dict[str, Any],
    ) -> str:
        return json.dumps(data)

    @staticmethod
    def deserialize_data(
        data: str,
    ) -> dict[str, Any]:
        return json.loads(data)