"""Local credentials, opaque-session, and Google OIDC primitives."""

import base64
import hashlib
import hmac
import json
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt

from app.core.config import Settings

_PASSWORD_N = 2**15
_PASSWORD_R = 8
_PASSWORD_P = 1
_PASSWORD_LENGTH = 32
_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


@dataclass(frozen=True)
class GoogleTransaction:
    state: str
    nonce: str
    verifier: str
    return_to: str
    expires_at: int


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def normalize_email(value: str) -> str | None:
    email = value.strip().casefold()
    if len(email) > 320 or any(character.isspace() for character in email):
        return None
    local, separator, domain = email.partition("@")
    return email if separator and local and "." in domain and not domain.startswith(".") else None


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=_PASSWORD_N,
        r=_PASSWORD_R,
        p=_PASSWORD_P,
        dklen=_PASSWORD_LENGTH,
        maxmem=64_000_000,
    )
    return f"scrypt${_PASSWORD_N}${_PASSWORD_R}${_PASSWORD_P}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    if stored is None:
        return False
    try:
        algorithm, n, r, p, encoded_salt, encoded_digest = stored.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=_decode(encoded_salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=_PASSWORD_LENGTH,
            maxmem=64_000_000,
        )
        return hmac.compare_digest(digest, _decode(encoded_digest))
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str, settings: Settings) -> str:
    secret = settings.auth_session_secret
    if secret is None or not secret.get_secret_value():
        raise ValueError("Local authentication is not configured")
    return hmac.new(secret.get_secret_value().encode(), token.encode(), hashlib.sha256).hexdigest()


def valid_return_to(value: str | None) -> str:
    return value if value and value.startswith("/") and not value.startswith("//") else "/dashboard"


def new_google_transaction(return_to: str, lifetime_seconds: int) -> GoogleTransaction:
    return GoogleTransaction(
        state=secrets.token_urlsafe(32),
        nonce=secrets.token_urlsafe(32),
        verifier=secrets.token_urlsafe(64),
        return_to=valid_return_to(return_to),
        expires_at=int((datetime.now(UTC) + timedelta(seconds=lifetime_seconds)).timestamp()),
    )


def encode_google_transaction(transaction: GoogleTransaction, settings: Settings) -> str:
    secret = settings.auth_state_secret
    if secret is None or not secret.get_secret_value():
        raise ValueError("Google authentication is not configured")
    payload = json.dumps(transaction.__dict__, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(secret.get_secret_value().encode(), payload, hashlib.sha256).digest()
    return f"{_encode(payload)}.{_encode(signature)}"


def decode_google_transaction(value: str | None, settings: Settings) -> GoogleTransaction | None:
    secret = settings.auth_state_secret
    if value is None or secret is None or not secret.get_secret_value():
        return None
    try:
        encoded_payload, encoded_signature = value.split(".")
        payload = _decode(encoded_payload)
        expected = hmac.new(secret.get_secret_value().encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _decode(encoded_signature)):
            return None
        transaction = GoogleTransaction(**json.loads(payload))
        return transaction if transaction.expires_at >= int(datetime.now(UTC).timestamp()) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def google_authorization_url(transaction: GoogleTransaction, settings: Settings) -> str:
    if not settings.auth_google_client_id:
        raise ValueError("Google authentication is not configured")
    challenge = _encode(hashlib.sha256(transaction.verifier.encode()).digest())
    params = {
        "client_id": settings.auth_google_client_id,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "nonce": transaction.nonce,
        "redirect_uri": str(settings.auth_google_redirect_uri),
        "response_type": "code",
        "scope": "openid email profile",
        "state": transaction.state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{httpx.QueryParams(params)}"


async def exchange_google_code(
    code: str, transaction: GoogleTransaction, settings: Settings
) -> str:
    if (
        not settings.auth_google_client_id
        or settings.auth_google_client_secret is None
        or not settings.auth_google_client_secret.get_secret_value()
    ):
        raise ValueError("Google authentication is not configured")
    payload = {
        "client_id": settings.auth_google_client_id,
        "client_secret": settings.auth_google_client_secret.get_secret_value(),
        "code": code,
        "code_verifier": transaction.verifier,
        "grant_type": "authorization_code",
        "redirect_uri": str(settings.auth_google_redirect_uri),
    }
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.post(_GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            id_token = response.json().get("id_token")
    except (httpx.HTTPError, ValueError, TypeError) as error:
        raise ValueError("Google authentication failed") from error
    if not isinstance(id_token, str):
        raise ValueError("Google authentication failed")
    return id_token


async def verified_google_claims(
    id_token: str, transaction: GoogleTransaction, settings: Settings
) -> Mapping[str, Any]:
    if not settings.auth_google_client_id:
        raise ValueError("Google authentication is not configured")
    try:
        header = jwt.get_unverified_header(id_token)
        key_id = header.get("kid")
        if header.get("alg") != "RS256" or not isinstance(key_id, str):
            raise ValueError("Google authentication failed")
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.get(_GOOGLE_JWKS_URL)
            response.raise_for_status()
        keys = jwt.PyJWKSet.from_dict(response.json()).keys
        key = next((candidate for candidate in keys if candidate.key_id == key_id), None)
        if key is None:
            raise ValueError("Google authentication failed")
        claims = jwt.decode(
            id_token,
            key=key.key,
            algorithms=["RS256"],
            audience=settings.auth_google_client_id,
            options={"require": ["aud", "email", "exp", "iss", "sub"]},
        )
    except (httpx.HTTPError, jwt.PyJWTError, StopIteration, TypeError, ValueError) as error:
        raise ValueError("Google authentication failed") from error
    if (
        not isinstance(claims, Mapping)
        or claims.get("iss") not in _GOOGLE_ISSUERS
        or claims.get("nonce") != transaction.nonce
        or claims.get("email_verified") is not True
        or (
            isinstance(claims.get("aud"), list)
            and claims.get("azp") != settings.auth_google_client_id
        )
    ):
        raise ValueError("Google authentication failed")
    return claims
