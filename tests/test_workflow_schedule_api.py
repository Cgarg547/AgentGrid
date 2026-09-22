from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _create_schedule():
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
    )

    assert response.status_code == 200

    return response.json()


def test_create_schedule():
    schedule = _create_schedule()

    assert schedule["schedule_id"]
    assert schedule["workflow_name"] == "research-pipeline"
    assert schedule["enabled"] is True
    assert schedule["next_run_at"]
    assert schedule["created_at"]

    client.delete(
        f"/schedules/{schedule['schedule_id']}"
    )


def test_list_schedules():
    schedule = _create_schedule()

    try:
        response = client.get("/schedules")

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
            f"/schedules/{schedule['schedule_id']}"
        )


def test_get_schedule():
    schedule = _create_schedule()

    try:
        response = client.get(
            f"/schedules/{schedule['schedule_id']}"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["schedule_id"] == schedule["schedule_id"]
        assert data["workflow_name"] == "research-pipeline"
        assert data["enabled"] is True

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}"
        )


def test_disable_schedule():
    schedule = _create_schedule()

    try:
        response = client.post(
            f"/schedules/{schedule['schedule_id']}/disable"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["schedule_id"] == schedule["schedule_id"]
        assert data["enabled"] is False

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}"
        )


def test_enable_schedule():
    schedule = _create_schedule()

    try:
        disable_response = client.post(
            f"/schedules/{schedule['schedule_id']}/disable"
        )

        assert disable_response.status_code == 200
        assert disable_response.json()["enabled"] is False

        enable_response = client.post(
            f"/schedules/{schedule['schedule_id']}/enable"
        )

        assert enable_response.status_code == 200

        data = enable_response.json()

        assert data["schedule_id"] == schedule["schedule_id"]
        assert data["enabled"] is True

    finally:
        client.delete(
            f"/schedules/{schedule['schedule_id']}"
        )


def test_delete_schedule():
    schedule = _create_schedule()

    response = client.delete(
        f"/schedules/{schedule['schedule_id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["schedule_id"] == schedule["schedule_id"]
    assert data["deleted"] is True

    get_response = client.get(
        f"/schedules/{schedule['schedule_id']}"
    )

    assert get_response.status_code == 404


def test_create_schedule_rejects_unknown_workflow():
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
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == (
        "Workflow 'does-not-exist' not found."
    )


def test_get_unknown_schedule_returns_404():
    schedule_id = "00000000-0000-0000-0000-000000000000"

    response = client.get(
        f"/schedules/{schedule_id}"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == (
        f"Schedule '{schedule_id}' not found."
    )