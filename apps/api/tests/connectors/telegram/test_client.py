import pytest

from app.connectors.telegram.client import TelegramClient, TelegramError


@pytest.mark.asyncio
async def test_telegram_mock_mode_requires_no_credentials_and_can_send() -> None:
    client = TelegramClient(mock_mode=True)
    bot = await client.get_me(None)
    await client.send_test_message(None, "demo-chat")
    assert bot.id == "mock-telegram-bot"


@pytest.mark.asyncio
async def test_telegram_rejects_missing_credentials_outside_mock_mode() -> None:
    with pytest.raises(TelegramError):
        await TelegramClient().get_me(None)
