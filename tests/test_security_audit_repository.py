from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.security_audit_event import SecurityAuditEvent
from app.services.security_audit_repository import SecurityAuditRepository


def create_repository():
    return SecurityAuditRepository(SessionLocal)


def create_event(
    *,
    key_id=None,
    action="workflow.execute",
    resource="research-pipeline",
    endpoint="POST /workflows/research-pipeline/execute",
    outcome="allowed",
    timestamp=None,
    metadata=None,
):
    return SecurityAuditEvent(
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
        metadata_json=SecurityAuditRepository.serialize_metadata(
            metadata
        ),
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


def test_save_and_get_event():
    repository = create_repository()

    event = create_event(
        key_id="key-test-1",
        metadata={
            "workflow_name": "research-pipeline",
        },
    )

    try:
        saved = repository.save(event)

        assert saved.event_id == event.event_id
        assert saved.key_id == "key-test-1"
        assert saved.action == "workflow.execute"
        assert saved.outcome == "allowed"

        loaded = repository.get(event.event_id)

        assert loaded is not None
        assert loaded.event_id == event.event_id
        assert loaded.resource == "research-pipeline"

    finally:
        delete_event(event.event_id)


def test_list_filters_by_key_id():
    repository = create_repository()

    matching = create_event(
        key_id="key-filter-1",
    )

    other = create_event(
        key_id="key-filter-2",
    )

    try:
        repository.save(matching)
        repository.save(other)

        events = repository.list(
            key_id="key-filter-1",
        )

        assert len(events) == 1
        assert events[0].event_id == matching.event_id

    finally:
        delete_event(matching.event_id)
        delete_event(other.event_id)


def test_list_filters_by_action_and_outcome():
    repository = create_repository()

    test_key_id = str(uuid4())

    allowed = create_event(
        key_id=test_key_id,
        action="workflow.execute",
        outcome="allowed",
    )

    denied = create_event(
        key_id=test_key_id,
        action="workflow.execute",
        outcome="denied",
    )

    different_action = create_event(
        key_id=test_key_id,
        action="workflow.pause",
        outcome="allowed",
    )

    try:
        repository.save(allowed)
        repository.save(denied)
        repository.save(different_action)

        events = repository.list(
            key_id=test_key_id,
            action="workflow.execute",
            outcome="allowed",
        )

        assert len(events) == 1
        assert events[0].event_id == allowed.event_id

    finally:
        delete_event(allowed.event_id)
        delete_event(denied.event_id)
        delete_event(different_action.event_id)


def test_list_filters_by_time_range():
    repository = create_repository()

    now = datetime.now(timezone.utc)

    before = create_event(
        timestamp=now - timedelta(hours=2),
    )

    inside = create_event(
        timestamp=now - timedelta(minutes=30),
    )

    after = create_event(
        timestamp=now + timedelta(hours=2),
    )

    try:
        repository.save(before)
        repository.save(inside)
        repository.save(after)

        events = repository.list(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )

        event_ids = {
            event.event_id
            for event in events
        }

        assert inside.event_id in event_ids
        assert before.event_id not in event_ids
        assert after.event_id not in event_ids

    finally:
        delete_event(before.event_id)
        delete_event(inside.event_id)
        delete_event(after.event_id)


def test_metadata_serialization_round_trip():
    metadata = {
        "workflow_name": "research-pipeline",
        "scope": "workflows:execute",
        "attempt": 1,
    }

    serialized = SecurityAuditRepository.serialize_metadata(
        metadata
    )

    restored = SecurityAuditRepository.deserialize_metadata(
        serialized
    )

    assert restored == metadata


def test_metadata_none_round_trip():
    serialized = SecurityAuditRepository.serialize_metadata(
        None
    )

    assert serialized is None

    restored = SecurityAuditRepository.deserialize_metadata(
        serialized
    )

    assert restored == {}