"""Authenticated, versioned encryption for connector credentials."""

import base64
import binascii
import hashlib
import os
from collections.abc import Iterable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_CONTEXT = b"pulseos:connector-secret:v1"


class SecretDecryptionError(ValueError):
    """Raised without exposing ciphertext or key details."""


def _decode_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.encode() + b"=" * (-len(value) % 4))
    except (ValueError, UnicodeEncodeError) as error:
        raise ValueError("Encryption keys must be urlsafe base64-encoded 256-bit values") from error
    if len(key) != 32:
        raise ValueError("Encryption keys must be urlsafe base64-encoded 256-bit values")
    return key


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


class SecretCipher:
    """AES-GCM envelope cipher supporting a current and retired master key set."""

    version = "v1"

    def __init__(self, current_key: str, previous_keys: Iterable[str] = ()) -> None:
        keys = [_decode_key(current_key), *(_decode_key(key) for key in previous_keys)]
        self._keys = {self._key_id(key): key for key in keys}
        self.current_key_id = self._key_id(keys[0])

    @staticmethod
    def _key_id(key: bytes) -> str:
        return hashlib.sha256(key).hexdigest()[:12]

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._keys[self.current_key_id]).encrypt(
            nonce, plaintext.encode(), _CONTEXT
        )
        return ".".join((self.version, self.current_key_id, _encode(nonce), _encode(ciphertext)))

    def decrypt(self, envelope: str) -> str:
        try:
            version, key_id, encoded_nonce, encoded_ciphertext = envelope.split(".")
            if version != self.version or key_id not in self._keys:
                raise SecretDecryptionError("Unable to decrypt connector secret")
            nonce = base64.urlsafe_b64decode(encoded_nonce + "=" * (-len(encoded_nonce) % 4))
            ciphertext = base64.urlsafe_b64decode(
                encoded_ciphertext + "=" * (-len(encoded_ciphertext) % 4)
            )
            return AESGCM(self._keys[key_id]).decrypt(nonce, ciphertext, _CONTEXT).decode()
        except (InvalidTag, UnicodeDecodeError, ValueError, binascii.Error) as error:
            if isinstance(error, SecretDecryptionError):
                raise
            raise SecretDecryptionError("Unable to decrypt connector secret") from None
