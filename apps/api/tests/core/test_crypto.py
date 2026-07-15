import base64
import logging

import pytest

from app.core.crypto import SecretCipher, SecretDecryptionError


def key(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def test_secret_cipher_round_trip_and_tamper_protection() -> None:
    cipher = SecretCipher(key(b"a" * 32))
    token = "connector-access-token"
    encrypted = cipher.encrypt(token)
    assert token not in encrypted
    assert cipher.decrypt(encrypted) == token
    with pytest.raises(SecretDecryptionError):
        cipher.decrypt(encrypted[:-1] + ("A" if encrypted[-1] != "A" else "B"))


def test_secret_cipher_supports_previous_key_and_hides_tokens_from_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    old_key, new_key = key(b"b" * 32), key(b"c" * 32)
    encrypted = SecretCipher(old_key).encrypt("refresh-token-value")
    with caplog.at_level(logging.DEBUG):
        assert SecretCipher(new_key, [old_key]).decrypt(encrypted) == "refresh-token-value"
    assert "refresh-token-value" not in caplog.text
    with pytest.raises(SecretDecryptionError):
        SecretCipher(new_key).decrypt("v1.bad.invalid.envelope")
