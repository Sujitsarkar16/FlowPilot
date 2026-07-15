from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest

from app.connectors.google.oauth import GOOGLE_SCOPES, GoogleOAuthClient
from app.core.config import Settings
from app.services.oauth_state import OAuthStateError, OAuthStateService


def test_google_authorization_url_has_required_scopes() -> None:
    client = GoogleOAuthClient(Settings(google_client_id="client-id"))
    query = parse_qs(urlparse(client.authorization_url("signed-state")).query)
    assert query["state"] == ["signed-state"]
    assert set(query["scope"][0].split()) == set(GOOGLE_SCOPES)


@pytest.mark.asyncio
async def test_oauth_state_is_provider_bound_and_single_use(session: object) -> None:
    states = OAuthStateService(
        "a-secure-test-signing-key-that-is-32-bytes", session  # type: ignore[arg-type]
    )
    user_id = uuid4()
    state = await states.issue(user_id, "google")
    assert await states.consume(state, "google") == user_id
    with pytest.raises(OAuthStateError):
        await states.consume(state, "google")
    with pytest.raises(OAuthStateError):
        await states.consume(await states.issue(user_id, "google"), "github")
