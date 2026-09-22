from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class WorkflowSchedule(Base):
    __tablename__ = "workflow_schedules"

    schedule_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    workflow_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )