"""Shared, constant-time verification for signed inbound webhooks."""

import hmac
from hashlib import sha256
from time import time


class WebhookVerificationError(Exception):
    """A webhook could not be authenticated within its allowed delivery window."""


def verify_hmac_signature(
    *, secret: str, timestamp: str | None, signature: str | None, body: bytes, window_seconds: int
) -> None:
    """Verify a timestamped SHA-256 HMAC without disclosing why verification failed."""
    try:
        timestamp_seconds = int(timestamp or "")
    except ValueError as error:
        raise WebhookVerificationError from error
    if abs(time() - timestamp_seconds) > window_seconds:
        raise WebhookVerificationError
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, sha256
    ).hexdigest()
    supplied = (signature or "").removeprefix("sha256=")
    if not hmac.compare_digest(supplied, expected):
        raise WebhookVerificationError
