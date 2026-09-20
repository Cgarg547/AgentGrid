from app.workflows.execution import WorkflowExecution


class ExecutionRepository:
    def __init__(self):
        self._executions: dict[str, WorkflowExecution] = {}

    def save(self, execution: WorkflowExecution) -> None:
        self._executions[execution.execution_id] = execution

    def get(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    def list(self) -> list[WorkflowExecution]:
        return list(self._executions.values())