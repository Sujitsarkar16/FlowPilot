"""Single source of truth for supported, executable action definitions."""

from collections.abc import Iterator, Mapping
from types import MappingProxyType

from app.connectors.base import ActionDefinition, ApprovalMode, ConnectorName, InputField
from app.models.enums import ConnectionProvider, RiskLevel


class ActionRegistryError(ValueError):
    """Raised when action definitions are invalid or not registered."""


class ActionRegistry:
    """A startup-populated registry with explicit duplicate and unknown rejection."""

    def __init__(self, definitions: tuple[ActionDefinition, ...] = ()) -> None:
        self._definitions: dict[str, ActionDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: ActionDefinition) -> None:
        if definition.action_type in self._definitions:
            raise ActionRegistryError(f"duplicate action registration: {definition.action_type}")
        self._definitions[definition.action_type] = definition

    def get(self, action_type: str) -> ActionDefinition:
        try:
            return self._definitions[action_type]
        except KeyError as error:
            raise ActionRegistryError(f"unknown action type: {action_type}") from error

    require = get

    def __contains__(self, action_type: object) -> bool:
        return isinstance(action_type, str) and action_type in self._definitions

    def __iter__(self) -> Iterator[ActionDefinition]:
        for action_type in sorted(self._definitions):
            yield self._definitions[action_type]

    @property
    def definitions(self) -> Mapping[str, ActionDefinition]:
        return MappingProxyType(dict(self._definitions))

    def frontend_metadata(self) -> list[dict[str, object]]:
        return [definition.frontend_metadata() for definition in self]


_GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
_GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def _definition(
    action_type: str,
    connector: ConnectorName,
    risk: RiskLevel,
    reversible: bool,
    scopes: tuple[str, ...],
    provider: ConnectionProvider | None,
    fields: dict[str, InputField],
    approval: ApprovalMode,
) -> ActionDefinition:
    return ActionDefinition(
        action_type=action_type,
        connector=connector,
        default_risk=risk,
        minimum_risk=risk,
        reversible=reversible,
        required_scopes=scopes,
        provider=provider,
        input_schema=fields,
        minimum_approval=approval,
    )


_EVENT_FIELDS = {
    "event_id": InputField("string", True, "Source life event identifier."),
    "event_type": InputField("string", True, "Source life event type."),
    "event_entities": InputField("object", False, "Structured event entities grouped by kind."),
}


def _fields(*optional: str) -> dict[str, InputField]:
    return {
        **_EVENT_FIELDS,
        **{name: InputField("string", False, "Safe optional planner input.") for name in optional},
    }


ACTION_REGISTRY = ActionRegistry(
    (
        _definition(
            "travel.create_folder",
            "google",
            RiskLevel.GREEN,
            True,
            (_GOOGLE_DRIVE_SCOPE,),
            ConnectionProvider.GOOGLE,
            _fields("folder_name"),
            "automatic",
        ),
        _definition(
            "travel.save_ticket",
            "google",
            RiskLevel.GREEN,
            True,
            (_GOOGLE_DRIVE_SCOPE,),
            ConnectionProvider.GOOGLE,
            _fields("ticket_name"),
            "automatic",
        ),
        _definition(
            "travel.upload_itinerary",
            "google",
            RiskLevel.GREEN,
            True,
            (_GOOGLE_DRIVE_SCOPE,),
            ConnectionProvider.GOOGLE,
            _fields("document_name"),
            "automatic",
        ),
        _definition(
            "travel.upload_packing_checklist",
            "google",
            RiskLevel.GREEN,
            True,
            (_GOOGLE_DRIVE_SCOPE,),
            ConnectionProvider.GOOGLE,
            _fields("document_name"),
            "automatic",
        ),
        _definition(
            "travel.create_calendar_event",
            "google",
            RiskLevel.GREEN,
            True,
            (_GOOGLE_CALENDAR_SCOPE,),
            ConnectionProvider.GOOGLE,
            _fields("calendar_title", "start_at"),
            "automatic",
        ),
        _definition(
            "travel.get_weather",
            "weather",
            RiskLevel.GREEN,
            True,
            (),
            None,
            _fields("location"),
            "automatic",
        ),
        _definition(
            "travel.generate_documents",
            "internal",
            RiskLevel.GREEN,
            True,
            (),
            None,
            _fields("checklist_title"),
            "automatic",
        ),
        _definition(
            "travel.notify_family",
            "telegram",
            RiskLevel.YELLOW,
            False,
            ("bot.send_messages",),
            ConnectionProvider.TELEGRAM,
            _fields("message"),
            "approval_required",
        ),
        _definition(
            "client.create_repository",
            "github",
            RiskLevel.YELLOW,
            False,
            ("repo",),
            ConnectionProvider.GITHUB,
            _fields("repository_name"),
            "approval_required",
        ),
        _definition(
            "client.generate_documents",
            "internal",
            RiskLevel.GREEN,
            True,
            (),
            None,
            _fields("proposal_title"),
            "automatic",
        ),
        _definition(
            "client.create_calendar_event",
            "google",
            RiskLevel.YELLOW,
            True,
            (_GOOGLE_CALENDAR_SCOPE,),
            ConnectionProvider.GOOGLE,
            _fields("calendar_title", "start_at"),
            "approval_required",
        ),
        _definition(
            "client.notify_client",
            "telegram",
            RiskLevel.YELLOW,
            False,
            ("bot.send_messages",),
            ConnectionProvider.TELEGRAM,
            _fields("message"),
            "approval_required",
        ),
        _definition(
            "salary.update_budget",
            "internal",
            RiskLevel.GREEN,
            True,
            (),
            None,
            _fields("budget_category"),
            "automatic",
        ),
        _definition(
            "salary.propose_transfer",
            "mock_bank",
            RiskLevel.RED,
            False,
            ("transfers:write",),
            ConnectionProvider.MOCK_BANK,
            _fields("amount", "currency", "destination"),
            "approval_required",
        ),
    )
)


def get_action_definition(action_type: str) -> ActionDefinition:
    """Return a registered definition or reject an unknown action type."""
    return ACTION_REGISTRY.get(action_type)


def frontend_action_metadata() -> list[dict[str, object]]:
    """Return stable, non-secret action catalog metadata for frontend consumers."""
    return ACTION_REGISTRY.frontend_metadata()
