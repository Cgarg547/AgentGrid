from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    name: str
    agent_name: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    name: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)

    def add_step(self, step: WorkflowStep) -> None:
        if any(existing.name == step.name for existing in self.steps):
            raise ValueError(
                f"Workflow step '{step.name}' already exists."
            )

        self.steps.append(step)

    def validate(self) -> None:
        step_names = {step.name for step in self.steps}

        for step in self.steps:
            for dependency in step.depends_on:
                if dependency not in step_names:
                    raise ValueError(
                        f"Step '{step.name}' depends on "
                        f"unknown step '{dependency}'."
                    )

    def get_ready_steps(self, completed_steps: set[str]) -> list[WorkflowStep]:
        ready_steps = []

        for step in self.steps:
            if step.name in completed_steps:
                continue

            dependencies_completed = all(
                dependency in completed_steps
                for dependency in step.depends_on
            )

            if dependencies_completed:
                ready_steps.append(step)

        return ready_steps

    def describe(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "name": step.name,
                    "agent_name": step.agent_name,
                    "depends_on": step.depends_on,
                }
                for step in self.steps
            ],
        }