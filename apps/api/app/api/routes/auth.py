"""Local email/password and Google OIDC authentication endpoints."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import Settings, get_settings
from app.db.repositories.sessions import UserSessionRepository
from app.db.repositories.users import UserRepository
from app.db.session import get_session
from app.models.user import User
from app.models.user_session import UserSession
from app.services.local_auth import (
    decode_google_transaction,
    encode_google_transaction,
    exchange_google_code,
    google_authorization_url,
    hash_password,
    hash_session_token,
    new_google_transaction,
    new_session_token,
    normalize_email,
    valid_return_to,
    verified_google_claims,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
_GOOGLE_STATE_COOKIE = "flowpilot_google_state"


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=1024)


def _origin(settings: Settings) -> str:
    return str(settings.auth_app_url).rstrip("/")


def _require_frontend_origin(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin != _origin(settings):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request origin")


def _require_session_secret(settings: Settings) -> None:
    if settings.auth_session_secret is None or not settings.auth_session_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth unavailable"
        )


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        settings.auth_cookie_name,
        token,
        domain=settings.auth_cookie_domain,
        httponly=True,
        max_age=settings.auth_session_lifetime_seconds,
        path="/",
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.auth_cookie_name, domain=settings.auth_cookie_domain, path="/")


def _set_google_state_cookie(response: Response, value: str, settings: Settings) -> None:
    response.set_cookie(
        _GOOGLE_STATE_COOKIE,
        value,
        domain=settings.auth_cookie_domain,
        httponly=True,
        max_age=settings.auth_google_state_lifetime_seconds,
        path="/api/v1/auth/google",
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )


def _clear_google_state_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        _GOOGLE_STATE_COOKIE, domain=settings.auth_cookie_domain, path="/api/v1/auth/google"
    )


async def _create_session(user: User, session: AsyncSession, settings: Settings) -> str:
    token = new_session_token()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.auth_session_lifetime_seconds)
    await UserSessionRepository(session).add(
        UserSession(
            user_id=user.id, token_hash=hash_session_token(token, settings), expires_at=expires_at
        )
    )
    return token


def _login_response(
    token: str, settings: Settings, status_code: int = status.HTTP_200_OK
) -> Response:
    response = Response(status_code=status_code)
    _set_session_cookie(response, token, settings)
    return response


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: Credentials,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    settings = get_settings()
    _require_session_secret(settings)
    _require_frontend_origin(request, settings)
    email = normalize_email(payload.email)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email"
        )
    users = UserRepository(session)
    # ponytail: Existing Supabase-era rows are not claimed by email; add a verified migration/linking
    # flow if they must be recovered, rather than letting a new credential take over prior data.
    if await users.get_by_email(email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    user = User(
        auth_subject=f"local:{uuid4()}", email=email, password_hash=hash_password(payload.password)
    )
    try:
        await users.add(user)
        token = await _create_session(user, session, settings)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
        ) from None
    return _login_response(token, settings, status.HTTP_201_CREATED)


@router.post("/login")
async def login(
    payload: Credentials,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Response:
    settings = get_settings()
    _require_session_secret(settings)
    _require_frontend_origin(request, settings)
    email = normalize_email(payload.email)
    user = await UserRepository(session).get_by_email(email) if email is not None else None
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    token = await _create_session(user, session, settings)
    await session.commit()
    return _login_response(token, settings)


@router.get("/session")
async def session_status(current_user: User = Depends(get_current_user)) -> dict[str, bool]:
    return {"authenticated": current_user.id is not None}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, session: AsyncSession = Depends(get_session)) -> Response:
    settings = get_settings()
    _require_session_secret(settings)
    _require_frontend_origin(request, settings)
    token = request.cookies.get(settings.auth_cookie_name)
    if token is not None:
        await UserSessionRepository(session).revoke_by_token_hash(
            hash_session_token(token, settings)
        )
        await session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response, settings)
    return response


@router.get("/google/start")
async def google_start(return_to: str | None = None) -> RedirectResponse:
    settings = get_settings()
    if (
        not settings.auth_google_client_id
        or settings.auth_google_client_secret is None
        or not settings.auth_google_client_secret.get_secret_value()
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google login unavailable"
        )
    try:
        transaction = new_google_transaction(
            valid_return_to(return_to), settings.auth_google_state_lifetime_seconds
        )
        response = RedirectResponse(
            google_authorization_url(transaction, settings), status_code=302
        )
        _set_google_state_cookie(
            response, encode_google_transaction(transaction, settings), settings
        )
        return response
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google login unavailable"
        ) from None


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    settings = get_settings()
    transaction = decode_google_transaction(request.cookies.get(_GOOGLE_STATE_COOKIE), settings)
    if (
        code is None
        or transaction is None
        or not secrets.compare_digest(state or "", transaction.state)
    ):
        return RedirectResponse(f"{_origin(settings)}/login?error=oauth", status_code=302)
    try:
        claims = await verified_google_claims(
            await exchange_google_code(code, transaction, settings), transaction, settings
        )
        subject = claims.get("sub")
        email = normalize_email(str(claims.get("email", "")))
        if not isinstance(subject, str) or not subject or email is None:
            raise ValueError("Google authentication failed")
        users = UserRepository(session)
        user = await users.get_by_google_subject(subject)
        if user is None:
            if await users.get_by_email(email) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Use your existing sign-in method"
                )
            name = claims.get("name")
            user = User(
                auth_subject=f"google:{subject}",
                email=email,
                display_name=name[:120] if isinstance(name, str) else None,
                google_subject=subject,
            )
            await users.add(user)
        else:
            user.email = email
        token = await _create_session(user, session, settings)
        await session.commit()
    except HTTPException:
        await session.rollback()
        return RedirectResponse(f"{_origin(settings)}/login?error=oauth", status_code=302)
    except (IntegrityError, ValueError):
        await session.rollback()
        return RedirectResponse(f"{_origin(settings)}/login?error=oauth", status_code=302)
    response = RedirectResponse(f"{_origin(settings)}{transaction.return_to}", status_code=302)
    _set_session_cookie(response, token, settings)
    _clear_google_state_cookie(response, settings)
    return response
