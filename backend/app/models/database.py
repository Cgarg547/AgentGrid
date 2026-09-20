from sqlalchemy import JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class WorkflowModel(Base):
    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

class WorkflowStepModel(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    workflow_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    step_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    agent_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    depends_on: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

class ExecutionModel(Base):
    __tablename__ = "executions"

    execution_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    workflow_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    step_statuses: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    step_results: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )