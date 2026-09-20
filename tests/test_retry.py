from app.workers.retry import RetryPolicy


def test_retry_policy_allows_retries():
    policy = RetryPolicy(max_attempts=3)

    assert policy.should_retry(1) is True
    assert policy.should_retry(2) is True
    assert policy.should_retry(3) is False


def test_retry_policy_can_disable_retries():
    policy = RetryPolicy(max_attempts=1)

    assert policy.should_retry(1) is False