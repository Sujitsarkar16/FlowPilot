"""Shared recursive redaction for durable audit payloads."""

from typing import Any

_REDACTED = "[redacted]"
_PROTECTED_KEY_PARTS = (
    "account",
    "authorization",
    "bank",
    "credential",
    "iban",
    "password",
    "pnr",
    "routing",
    "secret",
    "token",
    "webhook",
)


def redact(value: Any) -> Any:
    """Retain audit shape while removing secret and financial identifiers."""
    if isinstance(value, dict):
        return {
            key: _REDACTED
            if any(part in key.lower() for part in _PROTECTED_KEY_PARTS)
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    return value
