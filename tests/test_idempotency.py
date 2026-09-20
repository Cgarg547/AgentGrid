from uuid import uuid4

from app.workers.idempotency import IdempotencyStore


def test_idempotency_store_returns_none_for_unknown_task():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}"
    )

    result = store.get("unknown-task")

    assert result is None


def test_idempotency_store_saves_and_retrieves_result():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}"
    )

    task_id = "task-123"
    result = {
        "task_id": task_id,
        "status": "completed",
        "result": {
            "value": "success",
        },
    }

    store.set(task_id, result)

    stored = store.get(task_id)

    assert stored is not None
    assert stored["status"] == IdempotencyStore.COMPLETED_STATUS
    assert stored["result"] == result


def test_idempotency_store_deletes_result():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}"
    )

    task_id = "task-delete"

    store.set(
        task_id,
        {
            "task_id": task_id,
            "status": "completed",
        },
    )

    assert store.get(task_id) is not None

    store.delete(task_id)

    assert store.get(task_id) is None


def test_idempotency_store_claims_task_only_once():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}"
    )

    task_id = "task-claim"

    first_claim = store.claim(task_id)
    second_claim = store.claim(task_id)

    assert first_claim is True
    assert second_claim is False

    stored = store.get(task_id)

    assert stored == {
        "status": IdempotencyStore.CLAIMED_STATUS,
    }