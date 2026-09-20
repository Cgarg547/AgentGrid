from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import ExecutionModel
from app.models.execution import ExecutionRecord
from app.workflows.execution import WorkflowExecution


class PostgresExecutionRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(self, execution: WorkflowExecution) -> None:
        record = ExecutionRecord(
            execution_id=execution.execution_id,
            workflow_name=execution.workflow.name,
            status=execution.status.value,
            step_statuses={
                name: status.value
                for name, status in execution.step_statuses.items()
            },
            step_results=execution.step_results,
        )

        model = ExecutionModel(
            execution_id=record.execution_id,
            workflow_name=record.workflow_name,
            status=record.status,
            step_statuses=record.step_statuses,
            step_results=record.step_results,
        )

        with self.session_factory() as session:
            existing = session.get(
                ExecutionModel,
                execution.execution_id,
            )

            if existing is not None:
                existing.workflow_name = model.workflow_name
                existing.status = model.status
                existing.step_statuses = model.step_statuses
                existing.step_results = model.step_results
            else:
                session.add(model)

            session.commit()

    def get(self, execution_id: str) -> ExecutionRecord | None:
        with self.session_factory() as session:
            model = session.get(
                ExecutionModel,
                execution_id,
            )

            if model is None:
                return None

            return ExecutionRecord(
                execution_id=model.execution_id,
                workflow_name=model.workflow_name,
                status=model.status,
                step_statuses=model.step_statuses,
                step_results=model.step_results,
            )

    def list(self) -> list[ExecutionRecord]:
        with self.session_factory() as session:
            models = session.scalars(
                select(ExecutionModel)
            ).all()

            return [
                ExecutionRecord(
                    execution_id=model.execution_id,
                    workflow_name=model.workflow_name,
                    status=model.status,
                    step_statuses=model.step_statuses,
                    step_results=model.step_results,
                )
                for model in models
            ]