from app.workflows.workflow import Workflow


class WorkflowRegistry:
    def __init__(self):
        self._workflows: dict[str, Workflow] = {}

    def register(self, workflow: Workflow) -> None:
        if workflow.name in self._workflows:
            raise ValueError(
                f"Workflow '{workflow.name}' is already registered."
            )

        workflow.validate()
        self._workflows[workflow.name] = workflow

    def get(self, name: str) -> Workflow:
        workflow = self._workflows.get(name)

        if workflow is None:
            raise KeyError(
                f"Workflow '{name}' is not registered."
            )

        return workflow

    def list(self) -> list[Workflow]:
        return list(self._workflows.values())