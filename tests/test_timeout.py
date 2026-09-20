import pytest

from app.workers.timeout import TimeoutPolicy


def test_timeout_policy_defaults_to_30_seconds():
    policy = TimeoutPolicy()

    assert policy.get_timeout() == 30.0


def test_timeout_policy_accepts_custom_timeout():
    policy = TimeoutPolicy(timeout_seconds=10.0)

    assert policy.get_timeout() == 10.0


def test_timeout_policy_rejects_zero_timeout():
    with pytest.raises(ValueError, match="Timeout must be greater than 0."):
        TimeoutPolicy(timeout_seconds=0)


def test_timeout_policy_rejects_negative_timeout():
    with pytest.raises(ValueError, match="Timeout must be greater than 0."):
        TimeoutPolicy(timeout_seconds=-1)