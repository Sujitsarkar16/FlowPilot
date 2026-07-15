"""GitHub OAuth start and callback endpoints."""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.api.dependencies.auth import get_current_user
from app.api.routes.connections import get_connection_service
from app.api.routes.google_oauth import get_oauth_state_service
from app.connectors.github.oauth import (
    GITHUB_SCOPES,
    GitHubOAuthClient,
    GitHubOAuthError,
)
from app.core.config import get_settings
from app.models.enums import ConnectionProvider
from app.models.user import User
from app.schemas.connection import OAuthStartResponse
from app.services.connections import ConnectionService
from app.services.oauth_state import OAuthStateError, OAuthStateService

router = APIRouter(prefix="/api/v1/connections/github", tags=["connections"])


@router.post("/start", response_model=OAuthStartResponse)
async def start_github_oauth(
    current_user: User = Depends(get_current_user),
    states: OAuthStateService = Depends(get_oauth_state_service),
) -> OAuthStartResponse:
    try:
        state = await states.issue(current_user.id, ConnectionProvider.GITHUB.value)
        url = GitHubOAuthClient(get_settings()).authorization_url(state)
    except GitHubOAuthError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    return OAuthStartResponse(authorization_url=url)


@router.get("/callback")
async def complete_github_oauth(
    code: str,
    state: str,
    states: OAuthStateService = Depends(get_oauth_state_service),
    connections: ConnectionService = Depends(get_connection_service),
) -> RedirectResponse:
    try:
        user_id = await states.consume(state, ConnectionProvider.GITHUB.value)
    except OAuthStateError:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from None
    client = GitHubOAuthClient(get_settings())
    try:
        access_token = await client.exchange_code(code)
        identity = await client.identity(access_token)
        await connections.save(
            user_id,
            ConnectionProvider.GITHUB,
            identity.account_id,
            access_token=access_token,
            scopes=list(GITHUB_SCOPES),
            token_metadata={"login": identity.login},
        )
    except GitHubOAuthError:
        raise HTTPException(
            status_code=502, detail="GitHub connection could not be completed"
        ) from None
    return RedirectResponse(
        f"{get_settings().connection_success_url}?{urlencode({'connected': 'github'})}",
        status_code=303,
    )
