from typing import Any

from app.services.execution_checkpoint_repository import (
    ExecutionCheckpointRepository,
)


class ExecutionRecoveryService:
    def __init__(
        self,
        checkpoint_repository: ExecutionCheckpointRepository,
    ):
        self.checkpoint_repository = checkpoint_repository

    def recover_latest_state(
        self,
        execution_id: str,
    ) -> dict[str, Any] | None:
        checkpoint = (
            self.checkpoint_repository.get_latest(
                execution_id
            )
        )

        if checkpoint is None:
            return None

        durable_state = (
            self.checkpoint_repository.deserialize_state(
                checkpoint.state
            )
        )

        return {
            "execution_id": checkpoint.execution_id,
            "step_name": checkpoint.step_name,
            "status": checkpoint.status,
            "step_statuses": durable_state[
                "step_statuses"
            ],
            "step_results": durable_state[
                "step_results"
            ],
        }