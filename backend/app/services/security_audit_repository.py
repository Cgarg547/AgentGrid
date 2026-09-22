from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from app.models.security_audit_event import SecurityAuditEvent


class SecurityAuditRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(
        self,
        event: SecurityAuditEvent,
    ) -> SecurityAuditEvent:
        with self.session_factory() as session:
            session.add(event)
            session.commit()
            session.refresh(event)

            session.expunge(event)
            return event

    def get(
        self,
        event_id: str,
    ) -> SecurityAuditEvent | None:
        with self.session_factory() as session:
            event = session.get(
                SecurityAuditEvent,
                event_id,
            )

            if event is None:
                return None

            session.expunge(event)
            return event

    def list(
        self,
        key_id: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[SecurityAuditEvent]:
        with self.session_factory() as session:
            statement = select(SecurityAuditEvent)

            if key_id is not None:
                statement = statement.where(
                    SecurityAuditEvent.key_id == key_id
                )

            if action is not None:
                statement = statement.where(
                    SecurityAuditEvent.action == action
                )

            if outcome is not None:
                statement = statement.where(
                    SecurityAuditEvent.outcome == outcome
                )

            if start_time is not None:
                statement = statement.where(
                    SecurityAuditEvent.timestamp >= start_time
                )

            if end_time is not None:
                statement = statement.where(
                    SecurityAuditEvent.timestamp <= end_time
                )

            statement = statement.order_by(
                SecurityAuditEvent.timestamp.asc()
            )

            events = list(
                session.scalars(statement).all()
            )

            for event in events:
                session.expunge(event)

            return events

    @staticmethod
    def serialize_metadata(
        metadata: dict | None,
    ) -> str | None:
        if metadata is None:
            return None

        return json.dumps(metadata)

    @staticmethod
    def deserialize_metadata(
        metadata_json: str | None,
    ) -> dict:
        if not metadata_json:
            return {}

        return json.loads(metadata_json)