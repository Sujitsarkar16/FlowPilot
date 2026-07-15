"""Telegram connection request schemas."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class TelegramConnectionCreate(BaseModel):
    """Credentials arrive once, are encrypted, and are intentionally never returned."""

    model_config = ConfigDict(extra="forbid")

    bot_token: SecretStr | None = Field(default=None, min_length=1, max_length=512)
    chat_id: str = Field(min_length=1, max_length=128)
