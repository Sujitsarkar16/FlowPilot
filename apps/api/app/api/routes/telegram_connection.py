"""Telegram setup endpoint; test messages are handled by the generic test route."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import get_current_user
from app.api.routes.connections import get_connection_service
from app.connectors.telegram.client import TelegramClient, TelegramError
from app.core.config import get_settings
from app.models.connection import Connection
from app.models.enums import ConnectionProvider
from app.models.user import User
from app.schemas.connection import ConnectionRead
from app.schemas.telegram import TelegramConnectionCreate
from app.services.connections import ConnectionService

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


@router.post("/telegram", response_model=ConnectionRead, status_code=201)
async def connect_telegram(
    payload: TelegramConnectionCreate,
    current_user: User = Depends(get_current_user),
    connections: ConnectionService = Depends(get_connection_service),
) -> Connection:
    settings = get_settings()
    bot_token = payload.bot_token.get_secret_value() if payload.bot_token else None
    if not settings.telegram_mock_mode and not bot_token:
        raise HTTPException(status_code=422, detail="Telegram bot token is required")
    try:
        bot = await TelegramClient(mock_mode=settings.telegram_mock_mode).get_me(bot_token)
    except TelegramError:
        raise HTTPException(status_code=422, detail="Telegram rejected the bot token") from None
    return await connections.save(
        current_user.id,
        ConnectionProvider.TELEGRAM,
        bot.id,
        access_token=bot_token,
        scopes=["send_messages"],
        token_metadata={"chat_id": payload.chat_id, "bot_username": bot.username},
    )
