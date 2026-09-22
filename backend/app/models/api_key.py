from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    key_hash: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
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