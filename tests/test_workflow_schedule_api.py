from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.services.api_key_repository import APIKeyRepository
from app.services.api_key_service import APIKeyService


client = TestClient(app)

api_key_service = APIKeyService(
    APIKeyRepository(SessionLocal)
)


def create_test_key():
    return api_key_service.create_api_key(
        "schedule-api-test",
        scopes=[
            "workflows:execute",
        ],
    )


def auth_headers(raw_key):
    return {
        "Authorization": f"Bearer {raw_key}"
    }


def _create_schedule(raw_key):
    next_run_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=5)
    ).isoformat()

    response = client.post(
        "/schedules",
        json={
            "workflow_name": "research-pipeline",
            "next_run_at": next_run_at,
        },
        headers=auth_headers(raw_key),
    )

    assert response.status_code == 200

    return response.json()


def test_create_schedule():
    test_key, raw_key = create_test_key()
    schedule = _create_schedule(raw_key)

    try:
        assert schedule["schedule_id"]
        assert (
            schedule["workflow_name"]
            == "research-pipeline"
        )
        assert schedule["enabled"] is True
        assert schedule["next_run_at"]
        assert schedule["created_at"]

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_list_schedules():
    test_key, raw_key = create_test_key()
    schedule = _create_schedule(raw_key)

    try:
        response = client.get(
            "/schedules",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["count"] >= 1

        schedule_ids = {
            item["schedule_id"]
            for item in data["schedules"]
        }

        assert schedule["schedule_id"] in schedule_ids

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_get_schedule():
    test_key, raw_key = create_test_key()
    schedule = _create_schedule(raw_key)

    try:
        response = client.get(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["schedule_id"]
            == schedule["schedule_id"]
        )
        assert (
            data["workflow_name"]
            == "research-pipeline"
        )
        assert data["enabled"] is True

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_disable_schedule():
    test_key, raw_key = create_test_key()
    schedule = _create_schedule(raw_key)

    try:
        response = client.post(
            f"/schedules/{schedule['schedule_id']}/disable",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["schedule_id"]
            == schedule["schedule_id"]
        )
        assert data["enabled"] is False

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_enable_schedule():
    test_key, raw_key = create_test_key()
    schedule = _create_schedule(raw_key)

    try:
        disable_response = client.post(
            f"/schedules/{schedule['schedule_id']}/disable",
            headers=auth_headers(raw_key),
        )

        assert disable_response.status_code == 200
        assert (
            disable_response.json()["enabled"]
            is False
        )

        enable_response = client.post(
            f"/schedules/{schedule['schedule_id']}/enable",
            headers=auth_headers(raw_key),
        )

        assert enable_response.status_code == 200

        data = enable_response.json()

        assert (
            data["schedule_id"]
            == schedule["schedule_id"]
        )
        assert data["enabled"] is True

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_delete_schedule():
    test_key, raw_key = create_test_key()
    schedule = _create_schedule(raw_key)

    try:
        response = client.delete(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["schedule_id"]
            == schedule["schedule_id"]
        )
        assert data["deleted"] is True

        get_response = client.get(
            f"/schedules/{schedule['schedule_id']}",
            headers=auth_headers(raw_key),
        )

        assert get_response.status_code == 404

    finally:
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_create_schedule_rejects_unknown_workflow():
    test_key, raw_key = create_test_key()

    try:
        next_run_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=5)
        ).isoformat()

        response = client.post(
            "/schedules",
            json={
                "workflow_name": "does-not-exist",
                "next_run_at": next_run_at,
            },
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 404

        data = response.json()

        assert data["detail"] == (
            "Workflow 'does-not-exist' not found."
        )

    finally:
        api_key_service.delete_api_key(
            test_key.key_id
        )


def test_get_unknown_schedule_returns_404():
    test_key, raw_key = create_test_key()

    try:
        schedule_id = (
            "00000000-0000-0000-0000-000000000000"
        )

        response = client.get(
            f"/schedules/{schedule_id}",
            headers=auth_headers(raw_key),
        )

        assert response.status_code == 404

        data = response.json()

        assert data["detail"] == (
            f"Schedule '{schedule_id}' not found."
        )

    finally:
        api_key_service.delete_api_key(
            test_key.key_id
        )

def test_schedule_api_enforces_rate_limit():
    import fakeredis
    import app.security.rate_limit as rate_limit_module

    test_key, raw_key = create_test_key()

    fake_redis = fakeredis.FakeRedis()

    original_get_redis_client = rate_limit_module.get_redis_client
    original_rate_limit = rate_limit_module.RATE_LIMIT

    rate_limit_module.get_redis_client = lambda: fake_redis
    rate_limit_module.RATE_LIMIT = 1

    try:
        first_response = client.get(
            "/schedules",
            headers=auth_headers(raw_key),
        )

        second_response = client.get(
            "/schedules",
            headers=auth_headers(raw_key),
        )

    finally:
        rate_limit_module.get_redis_client = original_get_redis_client
        rate_limit_module.RATE_LIMIT = original_rate_limit

        api_key_service.delete_api_key(
            test_key.key_id
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"] == "Rate limit exceeded."
    assert second_response.headers["Retry-After"] == "60"