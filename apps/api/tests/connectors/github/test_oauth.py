from urllib.parse import parse_qs, urlparse

from app.connectors.github.oauth import GITHUB_SCOPES, GitHubOAuthClient
from app.core.config import Settings


def test_github_authorization_requests_only_minimal_repository_scope() -> None:
    client = GitHubOAuthClient(Settings(github_client_id="client-id"))
    query = parse_qs(urlparse(client.authorization_url("signed-state")).query)
    assert query["state"] == ["signed-state"]
    assert query["scope"] == [" ".join(GITHUB_SCOPES)]
