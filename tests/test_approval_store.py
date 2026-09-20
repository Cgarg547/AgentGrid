import uuid

import pytest

from app.security.approval import (
    ApprovalRequest,
    ApprovalStatus,
)
from app.security.approval_store import ApprovalStore


def test_approval_store_round_trip():
    request_id = f"test-{uuid.uuid4()}"

    store = ApprovalStore(
        key_prefix=f"test-approval:{uuid.uuid4()}"
    )

    request = ApprovalRequest(
        request_id=request_id,
        agent_name="researcher",
        tool_name="send_email",
    )

    try:
        store.save(request)

        loaded = store.get(request_id)

        assert loaded is not None
        assert loaded.request_id == request_id
        assert loaded.agent_name == "researcher"
        assert loaded.tool_name == "send_email"
        assert loaded.status == ApprovalStatus.PENDING
    finally:
        store.delete(request_id)


def test_approval_store_can_approve():
    request_id = f"test-{uuid.uuid4()}"

    store = ApprovalStore(
        key_prefix=f"test-approval:{uuid.uuid4()}"
    )

    request = ApprovalRequest(
        request_id=request_id,
        agent_name="researcher",
        tool_name="send_email",
    )

    try:
        store.save(request)

        approved = store.approve(request_id)

        assert approved.status == ApprovalStatus.APPROVED

        loaded = store.get(request_id)

        assert loaded is not None
        assert loaded.status == ApprovalStatus.APPROVED
    finally:
        store.delete(request_id)


def test_approval_store_can_reject():
    request_id = f"test-{uuid.uuid4()}"

    store = ApprovalStore(
        key_prefix=f"test-approval:{uuid.uuid4()}"
    )

    request = ApprovalRequest(
        request_id=request_id,
        agent_name="researcher",
        tool_name="send_email",
    )

    try:
        store.save(request)

        rejected = store.reject(request_id)

        assert rejected.status == ApprovalStatus.REJECTED

        loaded = store.get(request_id)

        assert loaded is not None
        assert loaded.status == ApprovalStatus.REJECTED
    finally:
        store.delete(request_id)


def test_approval_store_rejects_unknown_request():
    store = ApprovalStore(
        key_prefix=f"test-approval:{uuid.uuid4()}"
    )

    with pytest.raises(
        KeyError,
        match="not found",
    ):
        store.approve("does-not-exist")