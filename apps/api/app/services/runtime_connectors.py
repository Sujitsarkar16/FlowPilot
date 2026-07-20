"""Bind real provider adapters to the persisted action and its encrypted connection."""

from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from email.utils import parseaddr
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.connectors.base import Connector, ConnectorExecutionError, MockConnector
from app.connectors.github.repositories import GitHubRepositoryConnector
from app.connectors.google.calendar import GoogleCalendarConnector
from app.connectors.google.drive import GoogleDriveConnector
from app.connectors.google.gmail import GmailAuthenticationError, GmailClient, GmailError
from app.connectors.google.oauth import GoogleOAuthClient, OAuthProviderError
from app.connectors.internal.documents import InternalDocumentConnector
from app.connectors.telegram.actions import TelegramActionConnector
from app.connectors.weather.open_meteo import OpenMeteoConnector
from app.core.config import Settings, get_settings
from app.core.crypto import SecretCipher
from app.models.action import Action, ActionDependency
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.models.event import LifeEvent
from app.models.event_attachment import EventAttachment
from app.models.plan import Plan
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)
from app.services.connection_secrets import ConnectionSecrets
from app.services.connector_registry import ConnectorRegistry
from app.services.travel_ticket import TravelTicketService

_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
_SUBSCRIPTION_QUERY = (
    "newer_than:1y {subject:subscription subject:renewal subject:membership "
    'subject:"auto-renew" subject:recurring}'
)
_MAX_SUBSCRIPTION_CANDIDATES = 50
_MAX_SUBSCRIPTION_RESULTS = 20
_INACTIVE_SUBJECT_TERMS = ("cancelled", "canceled", "expired", "terminated")


class RuntimeConnector(Connector):
    """Resolve an action's connection immediately before a real provider call."""

    def __init__(self, name: str, session: AsyncSession, settings: Settings) -> None:
        self.name = name
        self._session = session
        self._settings = settings

    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        action, event = await self._action_context(action_id)
        if self.name == "google":
            return await self._google(action, event, idempotency_key, input)
        if self.name == "github":
            return await self._github(action, event, idempotency_key, input)
        if self.name == "telegram":
            return await self._telegram(action, event, idempotency_key, input)
        if self.name == "weather":
            return await self._weather(action, event, idempotency_key, input)
        if self.name == "internal":
            return await self._documents(action, event, idempotency_key, input)
        raise ConnectorExecutionError(ConnectorErrorCategory.PERMANENT, "Unsupported connector")

    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        action, event = await self._action_context(action_id)
        if action.action_type == "subscription.check_renewal":
            subscriptions = result.output.get("subscriptions")
            return (
                isinstance(subscriptions, list)
                and isinstance(result.output.get("count"), int)
                and result.output["count"] == len(subscriptions)
            )
        if action.action_type == "travel.save_ticket":
            if result.output.get("found") is False:
                return True
            attachment_id = result.output.get("attachment_id")
            if not isinstance(attachment_id, str):
                return False
            try:
                parsed_attachment_id = UUID(attachment_id)
            except ValueError:
                return False
            return (
                await self._session.scalar(
                    select(EventAttachment.id).where(
                        EventAttachment.id == parsed_attachment_id,
                        EventAttachment.user_id == action.plan.user_id,
                        EventAttachment.life_event_id == event.id,
                    )
                )
            ) is not None
        if self.name == "internal":
            if action.action_type == "salary.update_budget":
                return isinstance(result.output.get("content"), str) and bool(
                    result.output.get("filename")
                )
            documents = result.output.get("documents")
            return (
                isinstance(documents, list)
                and bool(documents)
                and all(isinstance(item, dict) and bool(item.get("content")) for item in documents)
            )
        if self.name == "weather":
            return await OpenMeteoConnector().verify(
                action_id=action_id, idempotency_key=idempotency_key, result=result
            )
        connector = await self._provider(action, event)
        return await connector.verify(
            action_id=action_id, idempotency_key=idempotency_key, result=result
        )

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        action, event = await self._action_context(action_id)
        if self.name in {"internal", "weather"} or action.action_type in {
            "travel.save_ticket",
            "subscription.check_renewal",
        }:
            return ConnectorRollbackResult(output={"rolled_back": False, "reason": "non_external"})
        connector = await self._provider(action, event)
        return await connector.rollback(action_id=action_id, rollback_payload=rollback_payload)

    async def _google(
        self,
        action: Action,
        event: LifeEvent,
        key: str,
        input: Mapping[str, Any],
    ) -> ConnectorExecutionResult:
        if action.action_type == "travel.save_ticket":
            return await TravelTicketService(self._session, self._settings).fetch(action, event)
        if action.action_type == "subscription.check_renewal":
            return await self._subscription_renewals(action)
        connector = await self._provider(action, event)
        if action.action_type.endswith("create_folder"):
            payload = {
                "folder_name": self._text(input, "folder_name") or f"FlowPilot - {event.summary}",
            }
        elif action.action_type in {
            "travel.upload_itinerary",
            "travel.upload_packing_checklist",
        }:
            folder_id = await self._trip_folder_id(action.id)
            if folder_id is None:
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.VALIDATION, "Trip folder is unavailable"
                )
            file_name, content = await self._travel_file(action, event)
            payload = {"folder_id": folder_id, "file_name": file_name, "content": content}
        else:
            payload = {
                "calendar_title": self._text(input, "calendar_title") or event.summary,
                "start_at": self._text(input, "start_at")
                or (
                    self._kickoff_start(event)
                    if action.action_type == "client.create_calendar_event"
                    else event.occurred_at.isoformat()
                ),
            }
        return await connector.execute(action_id=action.id, idempotency_key=key, input=payload)

    async def _subscription_renewals(self, action: Action) -> ConnectorExecutionResult:
        connections = list(
            await self._session.scalars(
                select(Connection)
                .where(
                    Connection.user_id == action.plan.user_id,
                    Connection.provider == ConnectionProvider.GOOGLE,
                    Connection.status == ConnectionStatus.CONNECTED,
                )
                .order_by(Connection.created_at.asc(), Connection.id.asc())
            )
        )
        connection = next((item for item in connections if _GMAIL_SCOPE in item.scopes), None)
        if connection is None:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION,
                "Connect Google with Gmail read access to check subscriptions",
            )
        gmail = GmailClient(self._settings)
        token = await self._get_google_token(connection)
        try:
            return await self._search_subscription_messages(gmail, token)
        except GmailAuthenticationError:
            token = await self._get_google_token(connection, force_refresh=True)
            try:
                return await self._search_subscription_messages(gmail, token)
            except GmailAuthenticationError as error:
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.AUTHORIZATION,
                    "Google connection requires reauthentication",
                ) from error
            except GmailError as error:
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.RETRYABLE, "Gmail subscription search failed"
                ) from error
        except GmailError as error:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.RETRYABLE, "Gmail subscription search failed"
            ) from error

    @staticmethod
    async def _search_subscription_messages(
        gmail: GmailClient, access_token: str
    ) -> ConnectorExecutionResult:
        page = await gmail.list_messages(
            access_token,
            query=_SUBSCRIPTION_QUERY,
            max_results=_MAX_SUBSCRIPTION_CANDIDATES,
        )
        subscriptions: list[dict[str, str]] = []
        seen_services: set[str] = set()
        for message_id in page.message_ids:
            message = await gmail.get_message(access_token, message_id)
            subject = message.subject.strip()
            if any(term in subject.casefold() for term in _INACTIVE_SUBJECT_TERMS):
                continue
            sender_name, sender_address = parseaddr(message.sender)
            sender_domain = sender_address.rpartition("@")[2]
            service = (sender_name.strip() or sender_domain or "Unknown service")[:120]
            service_key = service.casefold()
            if service_key in seen_services:
                continue
            seen_services.add(service_key)
            subscriptions.append(
                {
                    "service": service,
                    "subject": subject[:200],
                    "received_at": message.received_at.isoformat(),
                }
            )
            if len(subscriptions) == _MAX_SUBSCRIPTION_RESULTS:
                break
        count = len(subscriptions)
        return ConnectorExecutionResult(
            output={
                "found": count > 0,
                "count": count,
                "summary": (
                    f"Found {count} recent email{'s' if count != 1 else ''} that may indicate "
                    f"active subscription{'s' if count != 1 else ''}."
                    if count
                    else "No recent subscription or renewal emails were found."
                ),
                "subscriptions": subscriptions,
                "search_window": "1 year",
            }
        )

    async def _github(
        self,
        action: Action,
        event: LifeEvent,
        key: str,
        input: Mapping[str, Any],
    ) -> ConnectorExecutionResult:
        connector = await self._provider(action, event)
        name = self._text(input, "repository_name") or f"flowpilot-{str(action.id)[:8]}"
        documents = (await self._dependency_output(action.id, "client.generate_documents")).get(
            "documents", []
        )
        readme = next(
            (
                item.get("content")
                for item in documents
                if isinstance(item, dict)
                and item.get("document_type") == "client_requirements_summary"
                and isinstance(item.get("content"), str)
            ),
            None,
        )
        return await connector.execute(
            action_id=action.id,
            idempotency_key=key,
            input={"name": name, "description": event.summary, "private": True, "readme": readme},
        )

    async def _telegram(
        self, action: Action, event: LifeEvent, key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        connection = await self._connection(action.plan.user_id, ConnectionProvider.TELEGRAM)
        chat_id = connection.token_metadata.get("chat_id") if connection else None
        if not isinstance(chat_id, str) or not chat_id:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Telegram chat is unavailable"
            )
        connector = await self._provider(action, None, connection)
        return await connector.execute(
            action_id=action.id,
            idempotency_key=key,
            input={
                "chat_id": chat_id,
                "message": self._text(input, "message")
                or self._draft_message(action.action_type, event),
            },
        )

    def _draft_message(self, action_type: str, event: LifeEvent) -> str:
        if action_type == "travel.notify_family":
            return f"Family update: {event.summary}. The itinerary and packing checklist are ready."
        if action_type == "client.notify_client":
            client = self._entity_text(event, "client") or "there"
            return (
                f"Hi {client}, your workspace, proposal, and invoice template are ready. "
                f"Suggested kickoff: {self._kickoff_start(event)}."
            )
        return "FlowPilot update"

    async def _weather(
        self,
        action: Action,
        event: LifeEvent,
        key: str,
        input: Mapping[str, Any],
    ) -> ConnectorExecutionResult:
        location = (
            self._text(input, "location") or self._entity_text(event, "destination") or "Unknown"
        )
        trip_date = self._entity_text(event, "date") or self._entity_text(event, "travel_dates")
        try:
            date.fromisoformat(trip_date or "")
        except ValueError:
            trip_date = event.occurred_at.date().isoformat()
        return await OpenMeteoConnector().execute(
            action_id=action.id,
            idempotency_key=key,
            input={"location": location, "date": trip_date},
        )

    async def _documents(
        self,
        action: Action,
        event: LifeEvent,
        key: str,
        input: Mapping[str, Any],
    ) -> ConnectorExecutionResult:
        if action.action_type == "salary.update_budget":
            return self._salary_budget(event)
        types = (
            ("itinerary", "packing_checklist")
            if action.action_type == "travel.generate_documents"
            else ("client_requirements_summary", "proposal_draft", "invoice_template")
        )
        connector = InternalDocumentConnector()
        documents: list[dict[str, Any]] = []
        for document_type in types:
            result = await connector.execute(
                action_id=action.id,
                idempotency_key=f"{key}:{document_type}",
                input={"document_type": document_type, "event": event},
            )
            documents.append(result.output)
        return ConnectorExecutionResult(output={"documents": documents})

    async def _trip_folder_id(self, action_id: UUID) -> str | None:
        output = await self._dependency_output(action_id, "travel.create_folder")
        folder_id = output.get("folder_id")
        return folder_id if isinstance(folder_id, str) and folder_id else None

    async def _travel_file(self, action: Action, event: LifeEvent) -> tuple[str, str]:
        document_type = (
            "itinerary" if action.action_type == "travel.upload_itinerary" else "packing_checklist"
        )
        documents = (await self._dependency_output(action.id, "travel.generate_documents")).get(
            "documents", []
        )
        document = next(
            (
                item
                for item in documents
                if isinstance(item, dict) and item.get("document_type") == document_type
            ),
            None,
        )
        if not isinstance(document, dict) or not isinstance(document.get("content"), str):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, f"{document_type} is unavailable"
            )
        filename = document.get("filename")
        return (
            filename if isinstance(filename, str) and filename else f"{document_type}.md",
            document["content"],
        )

    async def _dependency_output(self, action_id: UUID, action_type: str) -> Mapping[str, Any]:
        output = await self._session.scalar(
            select(Action.execution_result)
            .join(ActionDependency, ActionDependency.depends_on_action_id == Action.id)
            .where(ActionDependency.action_id == action_id, Action.action_type == action_type)
        )
        return output if isinstance(output, Mapping) else {}

    def _salary_budget(self, event: LifeEvent) -> ConnectorExecutionResult:
        salary = next(
            (
                entity.value
                for entity in event.entities
                if entity.kind == "salary" and isinstance(entity.value, dict)
            ),
            None,
        )
        if not isinstance(salary, dict):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "Salary data is unavailable"
            )
        currency = salary.get("currency")
        if not isinstance(currency, str) or not currency:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "Salary currency is unavailable"
            )
        categories = ("rent", "savings", "investment", "discretionary", "month_spend")
        if not all(isinstance(salary.get(category), int | float) for category in categories):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "Salary allocations are invalid"
            )
        content = "category,amount,currency\n" + "\n".join(
            f"{category},{float(salary[category]):.2f},{currency}" for category in categories
        )
        warning = salary.get("overspending_warning")
        return ConnectorExecutionResult(
            output={
                "filename": f"budget-{event.id}.csv",
                "content_type": "text/csv",
                "content": content,
                "allocations": {category: salary[category] for category in categories},
                "overspending_warning": warning if isinstance(warning, str) and warning else None,
            }
        )

    def _kickoff_start(self, event: LifeEvent) -> str:
        day = event.occurred_at.date() + timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        return datetime.combine(
            day, time(self._settings.client_availability_start_hour), tzinfo=UTC
        ).isoformat()

    async def _provider(
        self,
        action: Action,
        event: LifeEvent | None,
        connection: Connection | None = None,
    ) -> Connector:
        if self.name == "weather":
            return OpenMeteoConnector()
        provider = {
            "google": ConnectionProvider.GOOGLE,
            "github": ConnectionProvider.GITHUB,
            "telegram": ConnectionProvider.TELEGRAM,
        }.get(self.name)
        if provider is None:
            raise ConnectorExecutionError(ConnectorErrorCategory.PERMANENT, "Unsupported connector")
        connection = connection or await self._connection(action.plan.user_id, provider)
        if self.name == "google":
            token = await self._get_google_token(connection)
            _drive_actions = {
                "travel.create_folder",
                "client.create_folder",
                "travel.upload_itinerary",
                "travel.upload_packing_checklist",
            }
            if action.action_type.endswith("create_folder") or action.action_type in _drive_actions:
                return GoogleDriveConnector(access_token_resolver=lambda: token)
            return GoogleCalendarConnector(access_token_resolver=lambda: token)
        token = self._sync_token(connection)
        if self.name == "github":
            return GitHubRepositoryConnector(access_token=token)
        return TelegramActionConnector(
            bot_token=token,
            mock_mode=self._settings.telegram_mock_mode,
        )

    async def _action_context(self, action_id: UUID) -> tuple[Action, LifeEvent]:
        statement = (
            select(Action)
            .options(
                joinedload(Action.plan).joinedload(Plan.source_event).joinedload(LifeEvent.entities)
            )
            .where(Action.id == action_id)
        )
        action = (await self._session.scalars(statement)).unique().one_or_none()
        if action is None:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.PERMANENT, "Action no longer exists"
            )
        return action, action.plan.source_event

    async def _connection(self, user_id: UUID, provider: ConnectionProvider) -> Connection:
        statement = select(Connection).where(
            Connection.user_id == user_id,
            Connection.provider == provider,
            Connection.status == ConnectionStatus.CONNECTED,
        )
        connection = await self._session.scalar(statement)
        if connection is None:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Provider connection is unavailable"
            )
        return connection

    async def _get_google_token(
        self, connection: Connection, *, force_refresh: bool = False
    ) -> str:
        """Return a Google access token, refreshing when missing or rejected."""
        key = self._settings.encryption_key
        if key is None:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Connection encryption is unavailable"
            )
        cipher = SecretCipher(
            key.get_secret_value(),
            [old.get_secret_value() for old in self._settings.encryption_previous_keys],
        )
        secrets_service = ConnectionSecrets(cipher)
        tokens = secrets_service.load(connection)
        if tokens.access_token and not force_refresh:
            return tokens.access_token
        # Access token missing, cleared, or rejected — attempt refresh
        if not tokens.refresh_token:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION,
                "Google token is unavailable and no refresh token is stored",
            )
        try:
            new_access_token = await GoogleOAuthClient(self._settings).refresh_access_token(
                tokens.refresh_token
            )
        except OAuthProviderError as exc:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, f"Google token refresh failed: {exc}"
            ) from exc
        secrets_service.save(connection, access_token=new_access_token)
        await self._session.commit()
        return new_access_token

    def _sync_token(self, connection: Connection) -> str:
        """Return the stored access token for non-Google providers (no refresh needed)."""
        key = self._settings.encryption_key
        if key is None:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Connection encryption is unavailable"
            )
        token = (
            ConnectionSecrets(
                SecretCipher(
                    key.get_secret_value(),
                    [old.get_secret_value() for old in self._settings.encryption_previous_keys],
                )
            )
            .load(connection)
            .access_token
        )
        if not token:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Provider token is unavailable"
            )
        return token

    @staticmethod
    def _text(input: Mapping[str, Any], name: str) -> str | None:
        value = input.get(name)
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _entity_text(event: LifeEvent, kind: str) -> str | None:
        for entity in event.entities:
            if entity.kind != kind or entity.is_sensitive:
                continue
            value: object = entity.value
            if isinstance(value, dict):
                value = next(
                    (value.get(key) for key in ("name", "date", "value", "text") if value.get(key)),
                    None,
                )
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None


def build_runtime_connector_registry(
    session: AsyncSession, settings: Settings | None = None
) -> ConnectorRegistry:
    """Create session-scoped real connectors; mocks remain available for isolated tests."""
    settings = settings or get_settings()
    return ConnectorRegistry(
        (
            RuntimeConnector("google", session, settings),
            RuntimeConnector("github", session, settings),
            RuntimeConnector("telegram", session, settings),
            RuntimeConnector("weather", session, settings),
            RuntimeConnector("internal", session, settings),
            MockConnector("mock_bank"),
        )
    )
