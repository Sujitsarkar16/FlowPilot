"""Authenticated user dependency backed only by verified Auth0 claims."""

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticationError, JWTVerifier
from app.core.config import get_settings
from app.core.rate_limit import RateLimitExceeded, rate_limit_bucket
from app.db.repositories.users import UserRepository
from app.db.session import get_session
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_jwt_verifier() -> JWTVerifier:
    """Keep the JWKS cache process-local and reusable across requests."""
    return JWTVerifier(get_settings())


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Return the local profile mapped from a verified JWT subject."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        claims = await get_jwt_verifier().verify(credentials.credentials)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        ) from None

    bucket = rate_limit_bucket(request.url.path)
    if bucket:
        try:
            await request.app.state.rate_limiter.check(bucket, f"user:{claims.subject}")
        except RateLimitExceeded as error:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error.detail,
                headers={"Retry-After": str(error.retry_after_seconds)},
            ) from None

    users = UserRepository(session)
    user = await users.get_by_subject(claims.subject)
    if user is None:
        user = await users.add(
            User(
                auth_subject=claims.subject,
                email=claims.email,
                display_name=claims.display_name,
            )
        )
    else:
        user.email = claims.email
        user.display_name = claims.display_name
    await session.commit()
    await session.refresh(user)
    return user
