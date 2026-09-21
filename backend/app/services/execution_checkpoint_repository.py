from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.execution_checkpoint import ExecutionCheckpoint


class ExecutionCheckpointRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(
        self,
        execution_id: str,
        step_name: str,
        status: str,
        state: dict[str, Any],
    ) -> ExecutionCheckpoint:
        checkpoint = ExecutionCheckpoint(
            execution_id=execution_id,
            step_name=step_name,
            status=status,
            state=json.dumps(state),
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(checkpoint)
        self.session.commit()
        self.session.refresh(checkpoint)

        return checkpoint

    def list_by_execution(
        self,
        execution_id: str,
    ) -> list[ExecutionCheckpoint]:
        return (
            self.session.query(ExecutionCheckpoint)
            .filter(
                ExecutionCheckpoint.execution_id
                == execution_id
            )
            .order_by(
                ExecutionCheckpoint.id.asc()
            )
            .all()
        )

    def get_latest(
        self,
        execution_id: str,
    ) -> ExecutionCheckpoint | None:
        return (
            self.session.query(ExecutionCheckpoint)
            .filter(
                ExecutionCheckpoint.execution_id
                == execution_id
            )
            .order_by(
                ExecutionCheckpoint.id.desc()
            )
            .first()
        )

    @staticmethod
    def deserialize_state(
        state: str,
    ) -> dict[str, Any]:
        return json.loads(state)