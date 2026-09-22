from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService
from app.services.security_audit_repository import SecurityAuditRepository
from app.services.security_audit_service import SecurityAuditService


client = TestClient(app)

api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)

audit_repository = SecurityAuditRepository(SessionLocal)

audit_service = SecurityAuditService(audit_repository)


def create_admin_api_key():
    api_key, raw_key = api_key_service.create_api_key(
        name=f"audit-admin-{uuid4()}",
        scopes=["api_keys:manage"],
    )

    return api_key, raw_key


def test_security_audit_api_requires_authentication():
    response = client.get("/security/audit")

    assert response.status_code == 401


def test_security_audit_api_requires_manage_scope():
    _, raw_key = api_key_service.create_api_key(
        name=f"audit-reader-{uuid4()}",
        scopes=["executions:read"],
    )

    response = client.get(
        "/security/audit",
        headers={
            "Authorization": f"Bearer {raw_key}",
        },
    )

    assert response.status_code == 403


def test_security_audit_api_lists_events():
    api_key, raw_key = create_admin_api_key()

    event = audit_service.record_event(
        key_id=api_key.key_id,
        action="test.audit.list",
        resource="test-resource",
        endpoint="GET /test",
        outcome="allowed",
        metadata={"source": "test"},
    )

    response = client.get(
        "/security/audit",
        params={
            "key_id": api_key.key_id,
            "action": "test.audit.list",
        },
        headers={
            "Authorization": f"Bearer {raw_key}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    matching_events = [
        item
        for item in data["events"]
        if item["event_id"] == event.event_id
    ]

    assert len(matching_events) == 1

    returned_event = matching_events[0]

    assert returned_event["key_id"] == api_key.key_id
    assert returned_event["action"] == "test.audit.list"
    assert returned_event["resource"] == "test-resource"
    assert returned_event["endpoint"] == "GET /test"
    assert returned_event["outcome"] == "allowed"
    assert returned_event["metadata"] == {
        "source": "test",
    }


def test_security_audit_api_filters_by_outcome():
    api_key, raw_key = create_admin_api_key()

    unique_action = f"test.audit.{uuid4()}"

    audit_service.record_event(
        key_id=api_key.key_id,
        action=unique_action,
        outcome="allowed",
    )

    audit_service.record_event(
        key_id=api_key.key_id,
        action=unique_action,
        outcome="denied",
    )

    response = client.get(
        "/security/audit",
        params={
            "key_id": api_key.key_id,
            "action": unique_action,
            "outcome": "denied",
        },
        headers={
            "Authorization": f"Bearer {raw_key}",
        },
    )

    assert response.status_code == 200

    events = response.json()["events"]

    assert len(events) == 1
    assert events[0]["outcome"] == "denied"


def test_security_audit_api_filters_by_time_range():
    _, raw_key = create_admin_api_key()

    unique_action = f"test.audit.time.{uuid4()}"

    old_time = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    current_time = datetime(
        2026,
        9,
        22,
        tzinfo=timezone.utc,
    )

    audit_service.record_event(
        key_id=None,
        action=unique_action,
        outcome="allowed",
        timestamp=old_time,
    )

    current_event = audit_service.record_event(
        key_id=None,
        action=unique_action,
        outcome="allowed",
        timestamp=current_time,
    )

    response = client.get(
        "/security/audit",
        params={
            "action": unique_action,
            "start_time": "2026-09-01T00:00:00Z",
            "end_time": "2026-09-30T23:59:59Z",
        },
        headers={
            "Authorization": f"Bearer {raw_key}",
        },
    )

    assert response.status_code == 200

    events = response.json()["events"]

    assert len(events) == 1
    assert events[0]["event_id"] == current_event.event_id

def test_security_audit_api_enforces_rate_limit():
    api_key, raw_key = create_admin_api_key()

    import fakeredis
    import app.security.rate_limit as rate_limit_module

    fake_redis = fakeredis.FakeRedis()

    original_get_redis_client = rate_limit_module.get_redis_client
    original_rate_limit = rate_limit_module.RATE_LIMIT

    rate_limit_module.get_redis_client = lambda: fake_redis
    rate_limit_module.RATE_LIMIT = 1

    try:
        first_response = client.get(
            "/security/audit",
            params={
                "key_id": api_key.key_id,
            },
            headers={
                "Authorization": f"Bearer {raw_key}",
            },
        )

        second_response = client.get(
            "/security/audit",
            params={
                "key_id": api_key.key_id,
            },
            headers={
                "Authorization": f"Bearer {raw_key}",
            },
        )
    finally:
        rate_limit_module.get_redis_client = original_get_redis_client
        rate_limit_module.RATE_LIMIT = original_rate_limit

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == "Rate limit exceeded."
    assert second_response.headers["Retry-After"] == "60"