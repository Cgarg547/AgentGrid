import pytest

from app.security.approval import (
    ApprovalRequest,
    ApprovalStatus,
)


def test_approval_request_starts_pending():
    request = ApprovalRequest(
        request_id="req-1",
        agent_name="researcher",
        tool_name="send_email",
    )

    assert request.status == ApprovalStatus.PENDING


def test_approval_request_can_be_approved():
    request = ApprovalRequest(
        request_id="req-2",
        agent_name="researcher",
        tool_name="send_email",
    )

    request.approve()

    assert request.status == ApprovalStatus.APPROVED


def test_approval_request_can_be_rejected():
    request = ApprovalRequest(
        request_id="req-3",
        agent_name="researcher",
        tool_name="send_email",
    )

    request.reject()

    assert request.status == ApprovalStatus.REJECTED


def test_approved_request_cannot_be_approved_again():
    request = ApprovalRequest(
        request_id="req-4",
        agent_name="researcher",
        tool_name="send_email",
    )

    request.approve()

    with pytest.raises(
        ValueError,
        match="Only pending approval requests",
    ):
        request.approve()


def test_rejected_request_cannot_be_rejected_again():
    request = ApprovalRequest(
        request_id="req-5",
        agent_name="researcher",
        tool_name="send_email",
    )

    request.reject()

    with pytest.raises(
        ValueError,
        match="Only pending approval requests",
    ):
        request.reject()