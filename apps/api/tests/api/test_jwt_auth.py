from time import monotonic

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.api.dependencies.auth import SupabaseTokenVerifier
from app.core.config import Settings


@pytest.mark.asyncio
async def test_verifier_accepts_only_a_signed_token_with_expected_claims() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://postgres:password@db.example.supabase.co:5432/postgres",
        supabase_url="https://project.supabase.co",
    )
    verifier = SupabaseTokenVerifier(settings)
    public_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk.update({"alg": "RS256", "kid": "current"})
    verifier._keys = {"current": jwt.PyJWK.from_dict(public_jwk)}
    verifier._expires_at = monotonic() + 60
    token = jwt.encode(
        {
            "aud": "authenticated",
            "email": "person@example.com",
            "exp": 4_102_444_800,
            "iss": "https://project.supabase.co/auth/v1",
            "sub": "user-123",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "current"},
    )

    assert await verifier.verify(token) == {
        "aud": "authenticated",
        "email": "person@example.com",
        "exp": 4_102_444_800,
        "iss": "https://project.supabase.co/auth/v1",
        "sub": "user-123",
    }
