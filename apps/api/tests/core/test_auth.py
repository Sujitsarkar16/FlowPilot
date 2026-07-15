import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.auth import AuthenticationError, JWTVerifier
from app.core.config import Settings


def token_and_jwks(*, audience: str = "authenticated", expired: bool = False) -> tuple[str, dict]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="test-key", alg="RS256", use="sig")
    claims = {
        "sub": "supabase-user",
        "aud": audience,
        "iss": "https://example.supabase.co/auth/v1",
        "exp": datetime.now(UTC) + timedelta(minutes=-1 if expired else 5),
        "email": "person@example.com",
        "user_metadata": {"full_name": "Pulse User"},
    }
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"}), {"keys": [jwk]}


@pytest.mark.asyncio
async def test_verifier_validates_claims_and_caches_jwks() -> None:
    token, jwks = token_and_jwks()
    calls = 0

    async def fetch_jwks() -> dict:
        nonlocal calls
        calls += 1
        return jwks

    verifier = JWTVerifier(Settings(supabase_url="https://example.supabase.co"), fetch_jwks)
    claims = await verifier.verify(token)
    assert (claims.subject, claims.email, claims.display_name) == (
        "supabase-user",
        "person@example.com",
        "Pulse User",
    )
    await verifier.verify(token)
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("audience,expired", [("wrong-audience", False), ("authenticated", True)])
async def test_verifier_rejects_invalid_claims(audience: str, expired: bool) -> None:
    token, jwks = token_and_jwks(audience=audience, expired=expired)

    async def fetch_jwks() -> dict:
        return jwks

    verifier = JWTVerifier(Settings(supabase_url="https://example.supabase.co"), fetch_jwks)
    with pytest.raises(AuthenticationError):
        await verifier.verify(token)
    with pytest.raises(AuthenticationError):
        await verifier.verify("not-a-jwt")
