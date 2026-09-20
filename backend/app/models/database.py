from sqlalchemy import JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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