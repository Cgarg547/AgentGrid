from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.security_audit_event import SecurityAuditEvent
from app.services.security_audit_repository import SecurityAuditRepository
from app.services.security_audit_service import SecurityAuditService


def create_service():
    return SecurityAuditService(
        SecurityAuditRepository(SessionLocal)
    )


def delete_event(event_id):
    with SessionLocal() as session:
        event = session.get(
            SecurityAuditEvent,
            event_id,
        )

        if event is not None:
            session.delete(event)
            session.commit()


def test_record_event_creates_persisted_audit_event():
    service = create_service()

    event = service.record_event(
        key_id="key-service-test",
        action="workflow.execute",
        resource="research-pipeline",
        endpoint="POST /workflows/research-pipeline/execute",
        outcome="allowed",
        metadata={
            "scope": "workflows:execute",
            "source": "test",
        },
    )

    try:
        assert event.event_id is not None
        assert event.key_id == "key-service-test"
        assert event.action == "workflow.execute"
        assert event.resource == "research-pipeline"
        assert event.endpoint == (
            "POST /workflows/research-pipeline/execute"
        )
        assert event.outcome == "allowed"

        metadata = (
            SecurityAuditRepository.deserialize_metadata(
                event.metadata_json
            )
        )

        assert metadata == {
            "scope": "workflows:execute",
            "source": "test",
        }

    finally:
        delete_event(event.event_id)


def test_record_event_uses_supplied_timestamp():
    service = create_service()

    timestamp = datetime(
        2026,
        9,
        22,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    event = service.record_event(
        key_id="key-timestamp-test",
        action="workflow.read",
        outcome="allowed",
        timestamp=timestamp,
    )

    try:
        assert event.timestamp == timestamp
    finally:
        delete_event(event.event_id)


def test_record_event_supports_anonymous_event():
    service = create_service()

    event = service.record_event(
        key_id=None,
        action="authentication",
        endpoint="GET /workflows",
        outcome="denied",
        metadata={
            "reason": "missing_api_key",
        },
    )

    try:
        assert event.key_id is None
        assert event.action == "authentication"
        assert event.outcome == "denied"

        metadata = (
            SecurityAuditRepository.deserialize_metadata(
                event.metadata_json
            )
        )

        assert metadata["reason"] == "missing_api_key"

    finally:
        delete_event(event.event_id)