from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.security_audit_event import SecurityAuditEvent
from app.services.security_audit_repository import SecurityAuditRepository


class SecurityAuditService:
    def __init__(
        self,
        repository: SecurityAuditRepository,
    ):
        self.repository = repository

    def record_event(
        self,
        *,
        key_id: str | None,
        action: str,
        resource: str | None = None,
        endpoint: str | None = None,
        outcome: str,
        metadata: dict | None = None,
        timestamp: datetime | None = None,
    ) -> SecurityAuditEvent:
        event = SecurityAuditEvent(
            event_id=str(uuid4()),
            key_id=key_id,
            action=action,
            resource=resource,
            endpoint=endpoint,
            outcome=outcome,
            timestamp=(
                timestamp
                if timestamp is not None
                else datetime.now(timezone.utc)
            ),
            metadata_json=(
                self.repository.serialize_metadata(
                    metadata
                )
            ),
        )

        return self.repository.save(event)