"""Polling ingestion for relevant Gmail messages."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.google.gmail import (
    GmailAuthenticationError,
    GmailClient,
    GmailCursorExpired,
    GmailError,
)
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.schemas.gmail import GmailCursor, GmailRelevanceFilter
from app.services.connection_secrets import ConnectionSecrets
from app.services.event_ingestion import EventIngestionService
from app.services.event_normalizer import normalize


class GmailSyncError(Exception):
    """A sync failure which deliberately leaves the durable cursor unchanged."""


@dataclass(frozen=True)
class GmailSyncResult:
    connection_id: str
    cursor: str
    ingested: int
    duplicates: int
    skipped: int


class GmailSyncService:
    def __init__(
        self, session: AsyncSession, gmail: GmailClient, secrets: ConnectionSecrets
    ) -> None:
        self._session = session
        self._gmail = gmail
        self._secrets = secrets
        self._ingestion = EventIngestionService(session)

    async def sync_all(self) -> list[GmailSyncResult]:
        connections = list(
            await self._session.scalars(
                select(Connection).where(
                    Connection.provider == ConnectionProvider.GOOGLE,
                    Connection.status == ConnectionStatus.CONNECTED,
                )
            )
        )
        return [await self.sync_connection(connection) for connection in connections]

    async def sync_connection(
        self, connection: Connection, *, relevance_filter: GmailRelevanceFilter | None = None
    ) -> GmailSyncResult:
        if connection.provider is not ConnectionProvider.GOOGLE:
            raise GmailSyncError("Gmail sync requires a Google connection")
        filters = relevance_filter or GmailRelevanceFilter.from_metadata(connection.token_metadata)
        tokens = self._secrets.load(connection)
        if not tokens.access_token and not tokens.refresh_token:
            raise GmailSyncError("Google connection has no usable credentials")
        try:
            return await self._sync_with_access_token(connection, tokens.access_token, filters)
        except GmailAuthenticationError:
            if not tokens.refresh_token:
                raise GmailSyncError("Google connection requires reauthentication") from None
            refreshed = await self._gmail.refresh_access_token(tokens.refresh_token)
            self._secrets.save(connection, refreshed.access_token, refreshed.refresh_token)
            await self._session.commit()
            return await self._sync_with_access_token(connection, refreshed.access_token, filters)


    async def _sync_with_access_token(
        self,
        connection: Connection,
        access_token: str | None,
        filters: GmailRelevanceFilter,
    ) -> GmailSyncResult:
        if not access_token:
            if not self._secrets.load(connection).refresh_token:
                raise GmailSyncError("Google connection has no usable credentials")
            refreshed = await self._gmail.refresh_access_token(
                self._secrets.load(connection).refresh_token or ""
            )
            self._secrets.save(connection, refreshed.access_token, refreshed.refresh_token)
            await self._session.commit()
            access_token = refreshed.access_token
        cursor = self._cursor(connection)
        try:
            if cursor is None:
                return await self._initial_sync(connection, access_token, filters)
            return await self._history_sync(connection, access_token, filters, cursor.history_id)
        except GmailCursorExpired:
            return await self._initial_sync(connection, access_token, filters)
        except GmailAuthenticationError:
            raise
        except GmailError as error:
            raise GmailSyncError("Gmail synchronization failed") from error

    async def _initial_sync(
        self, connection: Connection, access_token: str, filters: GmailRelevanceFilter
    ) -> GmailSyncResult:
        # Capture the baseline first: messages arriving during import remain in the next history pass.
        cursor = await self._gmail.profile_history_id(access_token)
        message_ids: list[str] = []
        page_token: str | None = None
        seen_tokens: set[str] = set()
        while True:
            page = await self._gmail.list_messages(access_token, page_token=page_token)
            message_ids.extend(page.message_ids)
            if not page.next_page_token:
                break
            if page.next_page_token in seen_tokens:
                raise GmailSyncError("Gmail returned a repeated page token")
            seen_tokens.add(page.next_page_token)
            page_token = page.next_page_token
        ingested, duplicates, skipped = await self._ingest_messages(
            connection, access_token, message_ids, filters
        )
        await self._advance_cursor(connection, cursor)
        return GmailSyncResult(str(connection.id), cursor, ingested, duplicates, skipped)

    async def _history_sync(
        self,
        connection: Connection,
        access_token: str,
        filters: GmailRelevanceFilter,
        cursor: str,
    ) -> GmailSyncResult:
        message_ids: list[str] = []
        next_cursor = cursor
        page_token: str | None = None
        seen_tokens: set[str] = set()
        while True:
            page = await self._gmail.list_history(access_token, cursor, page_token=page_token)
            message_ids.extend(page.message_ids)
            if page.history_id:
                next_cursor = page.history_id
            if not page.next_page_token:
                break
            if page.next_page_token in seen_tokens:
                raise GmailSyncError("Gmail returned a repeated page token")
            seen_tokens.add(page.next_page_token)
            page_token = page.next_page_token
        ingested, duplicates, skipped = await self._ingest_messages(
            connection, access_token, message_ids, filters
        )
        await self._advance_cursor(connection, next_cursor)
        return GmailSyncResult(str(connection.id), next_cursor, ingested, duplicates, skipped)


    async def _ingest_messages(
        self,
        connection: Connection,
        access_token: str,
        message_ids: list[str],
        filters: GmailRelevanceFilter,
    ) -> tuple[int, int, int]:
        ingested = duplicates = skipped = 0
        for message_id in dict.fromkeys(message_ids):
            message = await self._gmail.get_message(access_token, message_id)
            if not filters.matches(message):
                skipped += 1
                continue
            result = await self._ingestion.ingest(connection.user_id, normalize(message.as_source()))
            if result.is_duplicate:
                duplicates += 1
            else:
                ingested += 1
        return ingested, duplicates, skipped

    @staticmethod
    def _cursor(connection: Connection) -> GmailCursor | None:
        value = connection.token_metadata.get("gmail_history_id")
        if not isinstance(value, str) or not value:
            return None
        try:
            return GmailCursor(history_id=value)
        except ValueError:
            return None

    async def _advance_cursor(self, connection: Connection, cursor: str) -> None:
        """Persist only after every selected message was ingested or idempotently observed."""
        connection.token_metadata = {**connection.token_metadata, "gmail_history_id": cursor}
        await self._session.commit()
