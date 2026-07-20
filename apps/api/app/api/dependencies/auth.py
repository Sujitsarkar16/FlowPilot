"""Local cookie-session FastAPI dependencies."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import RateLimitExceeded, rate_limit_bucket
from app.db.repositories.sessions import UserSessionRepository
from app.db.session import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.services.local_auth import hash_session_token


def not_authenticated() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Load the locally owned user associated with a revocable opaque cookie."""
    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    if token is None:
        raise not_authenticated()
    try:
        token_hash = hash_session_token(token, settings)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth unavailable"
        ) from None
    record = await UserSessionRepository(session).get_active_by_token_hash(token_hash)
    if record is None:
        raise not_authenticated()
    bucket = rate_limit_bucket(request.url.path)
    if bucket:
        try:
            await request.app.state.rate_limiter.check(bucket, f"user:{record.user_id}")
        except RateLimitExceeded as error:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error.detail,
                headers={"Retry-After": str(error.retry_after_seconds)},
            ) from None
    return record.user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require a role assigned through trusted database administration."""
    if current_user.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required"
        )
    return current_user
