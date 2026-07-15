"""Safe schemas for connection management endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ConnectionProvider, ConnectionStatus


class ConnectionRead(BaseModel):
    """Public connection projection; encrypted credentials are never serialized."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: ConnectionProvider
    provider_account_id: str
    status: ConnectionStatus
    scopes: list[str]
    created_at: datetime
    updated_at: datetime


class OAuthStartResponse(BaseModel):
    authorization_url: str
