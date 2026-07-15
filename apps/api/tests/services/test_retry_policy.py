from datetime import UTC, datetime

from app.schemas.connector import ConnectorErrorCategory
from app.services.retry_policy import RetryPolicy


def test_retry_policy_retries_only_transient_failures_with_bounded_backoff() -> None:
    policy = RetryPolicy(maximum_attempts=3, base_delay_seconds=10)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    assert policy.should_retry(ConnectorErrorCategory.RETRYABLE, 2)
    assert not policy.should_retry(ConnectorErrorCategory.RETRYABLE, 3)
    assert not policy.should_retry(ConnectorErrorCategory.AUTHORIZATION, 1)
    assert policy.next_run_at("job", 2, now) > now
