from app.core.config import Settings
from app.services.local_auth import (
    decode_google_transaction,
    encode_google_transaction,
    hash_password,
    hash_session_token,
    new_google_transaction,
    new_session_token,
    verify_password,
)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://postgres:password@db.example.test:5432/flowpilot",
        auth_session_secret="session-secret",
        auth_state_secret="state-secret",
    )


def test_local_passwords_and_sessions_are_not_stored_as_plaintext() -> None:
    password_hash = hash_password("correct-horse-battery-staple")
    assert password_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", password_hash)
    assert not verify_password("incorrect-password", password_hash)
    token = new_session_token()
    assert hash_session_token(token, settings()) != token


def test_google_transaction_rejects_tampering() -> None:
    transaction = new_google_transaction("/dashboard", 600)
    encoded = encode_google_transaction(transaction, settings())
    assert decode_google_transaction(encoded, settings()) == transaction
    assert decode_google_transaction(f"{encoded}x", settings()) is None
