"""Google OAuth start and callback endpoints."""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.routes.connections import get_connection_service
from app.connectors.google.oauth import GoogleOAuthClient, OAuthProviderError
from app.core.config import get_settings
from app.db.session import get_session
from app.models.enums import ConnectionProvider
from app.models.user import User
from app.schemas.connection import OAuthStartResponse
from app.services.connections import ConnectionService
from app.services.oauth_state import OAuthStateError, OAuthStateService

router = APIRouter(prefix="/api/v1/connections/google", tags=["connections"])


def get_oauth_state_service(
    session: AsyncSession = Depends(get_session),
) -> OAuthStateService:
    key = get_settings().encryption_key
    if key is None:
        raise HTTPException(status_code=503, detail="OAuth state signing is not configured")
    return OAuthStateService(key.get_secret_value(), session)


@router.post("/start", response_model=OAuthStartResponse)
async def start_google_oauth(
    current_user: User = Depends(get_current_user),
    states: OAuthStateService = Depends(get_oauth_state_service),
) -> OAuthStartResponse:
    try:
        state = await states.issue(current_user.id, ConnectionProvider.GOOGLE.value)
        url = GoogleOAuthClient(get_settings()).authorization_url(state)
    except OAuthProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    return OAuthStartResponse(authorization_url=url)


@router.get("/callback")
async def complete_google_oauth(
    code: str,
    state: str,
    states: OAuthStateService = Depends(get_oauth_state_service),
    connections: ConnectionService = Depends(get_connection_service),
) -> RedirectResponse:
    try:
        user_id = await states.consume(state, ConnectionProvider.GOOGLE.value)
    except OAuthStateError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from None
    client = GoogleOAuthClient(get_settings())
    try:
        tokens = await client.exchange_code(code)
        identity = await client.identity(tokens.access_token)
        await connections.save(
            user_id,
            ConnectionProvider.GOOGLE,
            identity.account_id,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            scopes=tokens.scopes,
            token_metadata={"email": identity.email},
        )
    except OAuthProviderError:
        raise HTTPException(
            status_code=502, detail="Google connection could not be completed"
        ) from None
    return RedirectResponse(
        f"{get_settings().connection_success_url}?{urlencode({'connected': 'google'})}",
        status_code=303,
    )
