from app.models.approval_api import ApprovalResponse


def test_approval_response():
    response = ApprovalResponse(
        request_id="req-123",
        agent_name="researcher",
        tool_name="send_email",
        status="pending",
    )

    assert response.request_id == "req-123"
    assert response.agent_name == "researcher"
    assert response.tool_name == "send_email"
    assert response.status == "pending"