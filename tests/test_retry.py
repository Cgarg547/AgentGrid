from app.workers.retry import RetryPolicy


def test_retry_policy_allows_retries():
    policy = RetryPolicy(max_attempts=3)

    assert policy.should_retry(1) is True
    assert policy.should_retry(2) is True
    assert policy.should_retry(3) is False


def test_retry_policy_can_disable_retries():
    policy = RetryPolicy(max_attempts=1)

    assert policy.should_retry(1) is False


def test_retry_policy_calculates_exponential_backoff():
    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
    )

    assert policy.get_delay(1) == 1.0
    assert policy.get_delay(2) == 2.0
    assert policy.get_delay(3) == 4.0


def test_retry_policy_rejects_invalid_attempt():
    policy = RetryPolicy()

    try:
        policy.get_delay(0)
    except ValueError as exc:
        assert str(exc) == "Attempt must be at least 1."
    else:
        raise AssertionError("Expected ValueError for invalid attempt.")