from app.security.policy import (
    PolicyDecision,
    ToolPolicy,
)


def test_policy_allows_tool():
    policy = ToolPolicy(
        tool_name="search",
    )

    assert policy.evaluate() == PolicyDecision.ALLOW


def test_policy_denies_tool():
    policy = ToolPolicy(
        tool_name="delete_database",
        allowed=False,
    )

    assert policy.evaluate() == PolicyDecision.DENY


def test_policy_requires_approval():
    policy = ToolPolicy(
        tool_name="send_email",
        require_approval=True,
    )

    assert (
        policy.evaluate()
        == PolicyDecision.REQUIRE_APPROVAL
    )