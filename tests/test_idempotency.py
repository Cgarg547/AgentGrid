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

def test_idempotency_store_allows_reclaim_after_claim_expires():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}",
        claim_ttl_seconds=1,
    )

    task_id = "task-expiring-claim"

    assert store.claim(task_id) is True
    assert store.claim(task_id) is False

    import time

    time.sleep(1.1)

    assert store.claim(task_id) is True


def test_idempotency_store_can_renew_claim():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}",
        claim_ttl_seconds=2,
    )

    task_id = "task-renew"

    assert store.claim(task_id) is True
    assert store.renew_claim(task_id) is True

    stored = store.get(task_id)

    assert stored == {
        "status": IdempotencyStore.CLAIMED_STATUS,
    }

def test_idempotency_store_renew_claim_requires_matching_owner():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}",
        claim_ttl_seconds=2,
    )

    task_id = "task-owner"

    assert store.claim(task_id, owner_id="worker-a") is True

    assert (
        store.renew_claim(
            task_id,
            owner_id="worker-b",
        )
        is False
    )

    assert (
        store.renew_claim(
            task_id,
            owner_id="worker-a",
        )
        is True
    )

def test_idempotency_store_delete_requires_matching_owner():
    store = IdempotencyStore(
        key_prefix=f"test-agentgrid-idempotency-{uuid4()}",
        claim_ttl_seconds=2,
    )

    task_id = "task-release-owner"

    assert store.claim(
        task_id,
        owner_id="worker-a",
    ) is True

    assert (
        store.delete(
            task_id,
            owner_id="worker-b",
        )
        is False
    )

    assert store.get(task_id) is not None

    assert (
        store.delete(
            task_id,
            owner_id="worker-a",
        )
        is True
    )

    assert store.get(task_id) is None