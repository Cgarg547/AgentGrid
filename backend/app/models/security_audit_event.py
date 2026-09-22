from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class SecurityAuditEvent(Base):
    __tablename__ = "security_audit_events"

    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    key_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    resource: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    endpoint: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )