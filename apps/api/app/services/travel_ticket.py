"""Secure, bounded Gmail ticket lookup for one owned travel event."""

import re
import unicodedata
from hashlib import sha256
from pathlib import PurePath
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import ConnectorExecutionError
from app.connectors.google.gmail import GmailAuthenticationError, GmailClient, GmailError
from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.db.repositories.events import EventRepository
from app.models.action import Action
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.models.event import LifeEvent
from app.models.event_attachment import EventAttachment
from app.schemas.connector import ConnectorErrorCategory, ConnectorExecutionResult
from app.schemas.gmail import GmailAttachment, GmailMessage
from app.schemas.raw_sources import MAX_ATTACHMENTS
from app.services.audit import AuditService
from app.services.connection_secrets import ConnectionSecrets, ConnectionTokens

_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
_MAX_CANDIDATES = 25
_TICKET_WORDS = ("ticket", "itinerary", "boarding", "booking", "confirmation")


class TravelTicketService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        gmail: GmailClient | None = None,
        secrets: ConnectionSecrets | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._gmail = gmail or GmailClient(settings)
        self._events = EventRepository(session)
        self._audit = AuditService(session)
        self._secrets = secrets or self._build_secrets(settings)

    async def fetch(self, action: Action, event: LifeEvent) -> ConnectorExecutionResult:
        if action.plan.user_id != event.user_id or action.plan.source_event_id != event.id:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.PERMANENT, "Ticket event ownership is invalid"
            )
        connection = await self._connection(action.plan.user_id)
        tokens = self._secrets.load(connection)
        access_token = tokens.access_token or await self._refresh(connection, tokens)
        try:
            return await self._find_and_save(action, event, access_token)
        except GmailAuthenticationError:
            access_token = await self._refresh(connection, tokens)
            try:
                return await self._find_and_save(action, event, access_token)
            except GmailAuthenticationError as error:
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.AUTHORIZATION,
                    "Google connection requires reauthentication",
                ) from error
            except GmailError as error:
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.RETRYABLE, "Gmail ticket search failed"
                ) from error
        except GmailError as error:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.RETRYABLE, "Gmail ticket search failed"
            ) from error

    async def _find_and_save(
        self, action: Action, event: LifeEvent, access_token: str
    ) -> ConnectorExecutionResult:
        identifiers, corroborators = self._evidence(event)
        if not identifiers:
            return ConnectorExecutionResult(
                output={"found": False, "reason": "insufficient_evidence"}
            )
        messages: list[GmailMessage] = []
        seen_ids: set[str] = set()
        for query in self._queries(identifiers):
            page = await self._gmail.list_messages(
                access_token, query=query, max_results=_MAX_CANDIDATES
            )
            batch = [message_id for message_id in page.message_ids if message_id not in seen_ids][
                :_MAX_CANDIDATES
            ]
            seen_ids.update(batch)
            messages.extend(
                [await self._gmail.get_message(access_token, message_id) for message_id in batch]
            )
            if any(
                self._score(message, identifiers, corroborators) is not None for message in messages
            ):
                break
        ranked = sorted(
            (
                (score, message)
                for message in messages
                if (score := self._score(message, identifiers, corroborators)) is not None
            ),
            key=lambda item: (-item[0], -item[1].received_at.timestamp(), item[1].message_id),
        )
        if not ranked:
            return ConnectorExecutionResult(output={"found": False, "reason": "no_verified_match"})
        message = ranked[0][1]
        pdf = self._best_pdf(message)
        if pdf is not None:
            if pdf.size_bytes > self._settings.event_attachment_max_bytes:
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.VALIDATION,
                    "The matching ticket exceeds the file limit",
                )
            content = await self._gmail.get_attachment(access_token, message.message_id, pdf)
            if not content.startswith(b"%PDF-"):
                raise GmailError("Gmail ticket attachment is not a PDF")
            filename, mime_type = self._safe_filename(pdf.name, "ticket.pdf"), "application/pdf"
        else:
            content = message.body.strip().encode("utf-8")
            if not content:
                return ConnectorExecutionResult(output={"found": False, "reason": "empty_match"})
            filename = f"ticket-email-{sha256(message.message_id.encode()).hexdigest()[:10]}.txt"
            mime_type = "text/plain"
        return await self._save(action, event, message, filename, mime_type, content)

    async def _save(
        self,
        action: Action,
        event: LifeEvent,
        message: GmailMessage,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> ConnectorExecutionResult:
        if len(content) > self._settings.event_attachment_max_bytes:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "The matching ticket exceeds the file limit"
            )
        digest = sha256(content).hexdigest()
        existing = await self._events.get_attachment_by_hash(event.user_id, event.id, digest)
        if existing is not None:
            return self._result(existing, message)
        if await self._events.attachment_count(event.user_id, event.id) >= MAX_ATTACHMENTS:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "The event folder is full"
            )
        attachment = EventAttachment(
            user_id=event.user_id,
            life_event_id=event.id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=digest,
            content=content,
        )
        self._session.add(attachment)
        self._audit.append_pending(
            user_id=event.user_id,
            life_event_id=event.id,
            plan_id=action.plan_id,
            action_id=action.id,
            event_name="gmail_ticket_saved",
            actor_type="system",
            payload={
                "name": filename,
                "mime_type": mime_type,
                "size_bytes": len(content),
                "source_message_hash": sha256(message.message_id.encode()).hexdigest(),
            },
        )
        await self._session.flush()
        return self._result(attachment, message)

    @staticmethod
    def _result(attachment: EventAttachment, message: GmailMessage) -> ConnectorExecutionResult:
        return ConnectorExecutionResult(
            output={
                "found": True,
                "attachment_id": str(attachment.id),
                "filename": attachment.filename,
                "mime_type": attachment.mime_type,
                "size_bytes": attachment.size_bytes,
                "source_message_hash": sha256(message.message_id.encode()).hexdigest(),
            }
        )

    async def _connection(self, user_id: UUID) -> Connection:
        connections = await self._session.scalars(
            select(Connection)
            .where(
                Connection.user_id == user_id,
                Connection.provider == ConnectionProvider.GOOGLE,
                Connection.status == ConnectionStatus.CONNECTED,
            )
            .order_by(Connection.created_at.asc(), Connection.id.asc())
        )
        # ponytail: use one deterministic Gmail-enabled account until account selection exists;
        # fan out and globally rank candidates when multi-account travel is supported.
        connection = next((item for item in connections if _GMAIL_SCOPE in item.scopes), None)
        if connection is None:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION,
                "Connect Google with Gmail read access to retrieve tickets",
            )
        return connection

    async def _refresh(self, connection: Connection, tokens: ConnectionTokens) -> str:
        if not tokens.refresh_token:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Google connection requires reauthentication"
            )
        try:
            refreshed = await self._gmail.refresh_access_token(tokens.refresh_token)
        except GmailError as error:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Google connection requires reauthentication"
            ) from error
        self._secrets.save(connection, refreshed.access_token, refreshed.refresh_token)
        await self._session.flush()
        return refreshed.access_token

    @staticmethod
    def _build_secrets(settings: Settings) -> ConnectionSecrets:
        if settings.encryption_key is None:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Connection encryption is unavailable"
            )
        return ConnectionSecrets(
            SecretCipher(
                settings.encryption_key.get_secret_value(),
                [key.get_secret_value() for key in settings.encryption_previous_keys],
            )
        )

    @staticmethod
    def _queries(identifiers: tuple[tuple[str, str], ...]) -> tuple[str, str]:
        alternatives = " ".join(value for _, value in identifiers[:4])
        common = (
            f"newer_than:2m {{ticket itinerary boarding booking confirmation}} {{{alternatives}}}"
        )
        return f"{common} has:attachment filename:pdf", common

    @classmethod
    def _score(
        cls,
        message: GmailMessage,
        identifiers: tuple[tuple[str, str], ...],
        corroborators: tuple[tuple[str, str], ...],
    ) -> int | None:
        attachment_names = " ".join(item.name for item in message.attachments)
        haystack = cls._normalize(
            " ".join((message.sender, message.subject, message.body, attachment_names))
        )
        matched_identifiers = [item for item in identifiers if cls._contains(haystack, item[1])]
        matched_corroborators = [item for item in corroborators if cls._contains(haystack, item[1])]
        pnr_match = any(kind == "pnr" for kind, value in matched_identifiers)
        flight_match = any(kind == "flight" for kind, value in matched_identifiers)
        if not pnr_match and not (flight_match and matched_corroborators):
            return None
        subject = cls._normalize(message.subject)
        return (
            (100 if pnr_match else 0)
            + (60 if flight_match else 0)
            + 15 * len(matched_corroborators)
            + (
                10
                if any(
                    item.mime_type.casefold() == "application/pdf" for item in message.attachments
                )
                else 0
            )
            + (5 if any(word in subject for word in _TICKET_WORDS) else 0)
        )

    @staticmethod
    def _evidence(
        event: LifeEvent,
    ) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
        identifiers: list[tuple[str, str]] = []
        corroborators: list[tuple[str, str]] = []
        identifier_kinds = {
            "pnr": "pnr",
            "booking_reference": "pnr",
            "confirmation": "pnr",
            "flight": "flight",
            "flight_number": "flight",
        }
        corroborator_kinds = {
            "destination": "destination",
            "airline": "airline",
            "date": "date",
            "travel_dates": "date",
        }
        for entity in event.entities:
            category = identifier_kinds.get(entity.kind)
            target = identifiers
            if category is None:
                category = corroborator_kinds.get(entity.kind)
                target = corroborators
            if category is None:
                continue
            for value in entity.value.values():
                if isinstance(value, str) and (term := TravelTicketService._safe_term(value)):
                    target.append((category, term))
        return tuple(dict.fromkeys(identifiers)), tuple(dict.fromkeys(corroborators))

    @staticmethod
    def _best_pdf(message: GmailMessage) -> GmailAttachment | None:
        pdfs = [
            attachment
            for attachment in message.attachments
            if attachment.mime_type.casefold() == "application/pdf"
            and (attachment.attachment_id or attachment.inline_data)
        ]
        if not pdfs:
            return None
        return min(
            pdfs,
            key=lambda item: (
                not any(word in item.name.casefold() for word in _TICKET_WORDS),
                item.size_bytes,
                item.name.casefold(),
            ),
        )

    @staticmethod
    def _safe_filename(value: str, fallback: str) -> str:
        return (
            value
            if value
            and len(value) <= 255
            and PurePath(value).name == value
            and "/" not in value
            and "\\" not in value
            and not any(ord(char) < 32 for char in value)
            else fallback
        )

    @staticmethod
    def _safe_term(value: str) -> str:
        value = unicodedata.normalize("NFKC", value).strip()[:80]
        return "".join(character for character in value if character.isalnum() or character == "-")

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

    @classmethod
    def _contains(cls, haystack: str, term: str) -> bool:
        compact = cls._compact(term)
        if len(compact) < 3:
            return False
        pattern = r"(?<!\w)" + r"[\W_]*".join(map(re.escape, compact)) + r"(?!\w)"
        return re.search(pattern, haystack) is not None

    @classmethod
    def _compact(cls, value: str) -> str:
        return re.sub(r"[^\w]", "", cls._normalize(value))
