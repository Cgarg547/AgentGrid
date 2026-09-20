from sqlalchemy import delete, select

from app.models.database import WorkflowModel, WorkflowStepModel
from app.workflows.workflow import Workflow, WorkflowStep


class PostgresWorkflowRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(self, workflow: Workflow) -> None:
        with self.session_factory() as session:
            existing = session.get(
                WorkflowModel,
                workflow.name,
            )

            if existing is not None:
                existing.description = workflow.description

                session.execute(
                    delete(WorkflowStepModel).where(
                        WorkflowStepModel.workflow_name
                        == workflow.name
                    )
                )
            else:
                session.add(
                    WorkflowModel(
                        name=workflow.name,
                        description=workflow.description,
                    )
                )

            for step in workflow.steps:
                session.add(
                    WorkflowStepModel(
                        workflow_name=workflow.name,
                        step_name=step.name,
                        agent_name=step.agent_name,
                        depends_on=step.depends_on,
                    )
                )

            session.commit()

    def get(self, workflow_name: str) -> Workflow | None:
        with self.session_factory() as session:
            workflow_model = session.get(
                WorkflowModel,
                workflow_name,
            )

            if workflow_model is None:
                return None

            step_models = session.scalars(
                select(WorkflowStepModel)
                .where(
                    WorkflowStepModel.workflow_name
                    == workflow_name
                )
                .order_by(WorkflowStepModel.id)
            ).all()

            workflow = Workflow(
                name=workflow_model.name,
                description=workflow_model.description,
            )

            for step_model in step_models:
                workflow.add_step(
                    WorkflowStep(
                        name=step_model.step_name,
                        agent_name=step_model.agent_name,
                        depends_on=step_model.depends_on,
                    )
                )

            return workflow

    def list(self) -> list[Workflow]:
        with self.session_factory() as session:
            workflow_models = session.scalars(
                select(WorkflowModel)
            ).all()

            workflows = []

            for workflow_model in workflow_models:
                step_models = session.scalars(
                    select(WorkflowStepModel)
                    .where(
                        WorkflowStepModel.workflow_name
                        == workflow_model.name
                    )
                    .order_by(WorkflowStepModel.id)
                ).all()

                workflow = Workflow(
                    name=workflow_model.name,
                    description=workflow_model.description,
                )

                for step_model in step_models:
                    workflow.add_step(
                        WorkflowStep(
                            name=step_model.step_name,
                            agent_name=step_model.agent_name,
                            depends_on=step_model.depends_on,
                        )
                    )

                workflows.append(workflow)

            return workflows
