"""Deterministic authorization policy for candidate actions."""

from collections.abc import Iterable, Mapping

from app.models.connection import Connection
from app.models.enums import (
    ActionStatus,
    AutonomyLevel,
    ConnectionProvider,
    ConnectionStatus,
    RiskLevel,
)
from app.schemas.policy import PolicyDecision, PolicyReason
from app.services.action_registry import ACTION_REGISTRY, ActionRegistry
from app.services.plan_graph import CandidateAction

# ─── Autonomy-level ordering ─────────────────────────────────────────────────
# Higher index = more autonomy.
_AUTONOMY_ORDER = [
    AutonomyLevel.OBSERVE,
    AutonomyLevel.SUGGEST,
    AutonomyLevel.SAFE_ACTIONS,
    AutonomyLevel.TRUSTED_WORKFLOWS,
]


def _autonomy_gte(level: AutonomyLevel, threshold: AutonomyLevel) -> bool:
    return _AUTONOMY_ORDER.index(level) >= _AUTONOMY_ORDER.index(threshold)


def action_category(action_type: str) -> str:
    """Map registered actions to the small set of user-configurable categories."""
    if action_type.endswith("create_calendar_event"):
        return "calendar"
    if ".notify_" in action_type or action_type.endswith("_notify") or action_type.endswith("notify_family"):
        return "messages"
    if action_type.startswith("subscription."):
        return "subscriptions"
    if action_type.startswith("travel."):
        return "travel"
    if action_type.startswith("client."):
        return "client"
    if action_type.startswith("salary."):
        return "finance"
    if (
        action_type.endswith("create_folder")
        or action_type.endswith("upload_itinerary")
        or action_type.endswith("upload_packing_checklist")
        or action_type.endswith("save_ticket")
        or action_type.endswith("generate_documents")
    ):
        return "drive"
    if action_type.startswith("github.") or action_type.endswith("create_repository"):
        return "github"
    return "other"


class PolicyEngine:
    """Evaluate execution readiness without persisting or mutating an action."""

    def __init__(self, registry: ActionRegistry = ACTION_REGISTRY) -> None:
        self._registry = registry

    def evaluate(
        self,
        action: CandidateAction,
        autonomy: AutonomyLevel,
        connections: Iterable[Connection],
        *,
        template_mode: str | None = None,
        category_behaviors: Mapping[str, AutonomyLevel | str] | None = None,
    ) -> PolicyDecision:
        """Return action fields after connector, immutable-risk, and user-policy checks."""
        definition = self._registry.get(action.action_type)
        connection_reason = _connection_reason(definition.provider, definition.required_scopes, connections)
        if connection_reason is not None:
            return _blocked(connection_reason, requires_approval=action.risk_level is RiskLevel.RED)
        mode = template_mode or action.approval_mode
        if mode == "blocked" or definition.minimum_approval == "blocked":
            return _blocked(PolicyReason.TEMPLATE_BLOCKED, requires_approval=action.risk_level is RiskLevel.RED)
        # Red actions always require approval regardless of autonomy level.
        if action.risk_level is RiskLevel.RED:
            return _approval(PolicyReason.RED_REQUIRES_APPROVAL)
        if mode == "approval_required" or definition.minimum_approval == "approval_required":
            return _approval(PolicyReason.ACTION_REQUIRES_APPROVAL)
        effective_autonomy = _effective_autonomy(action.action_type, autonomy, category_behaviors)
        # TRUSTED_WORKFLOWS: auto-execute green and yellow actions without approval.
        if _autonomy_gte(effective_autonomy, AutonomyLevel.TRUSTED_WORKFLOWS):
            return PolicyDecision(
                status=ActionStatus.PLANNED,
                requires_approval=False,
                reason=PolicyReason.TRUSTED_AUTOMATIC,
            )
        # SAFE_ACTIONS: auto-execute only green-risk actions.
        if _autonomy_gte(effective_autonomy, AutonomyLevel.SAFE_ACTIONS) and action.risk_level is RiskLevel.GREEN:
            return PolicyDecision(
                status=ActionStatus.PLANNED,
                requires_approval=False,
                reason=PolicyReason.SAFE_AUTOMATIC,
            )
        reason = (
            PolicyReason.SUGGEST_MANUAL
            if effective_autonomy is AutonomyLevel.SUGGEST
            else PolicyReason.OBSERVE_MANUAL
        )
        return PolicyDecision(status=ActionStatus.PLANNED, requires_approval=False, reason=reason)


def evaluate_candidate_action(
    action: CandidateAction,
    autonomy: AutonomyLevel,
    connections: Iterable[Connection],
    *,
    template_mode: str | None = None,
) -> PolicyDecision:
    return PolicyEngine().evaluate(action, autonomy, connections, template_mode=template_mode)


def _effective_autonomy(
    action_type: str, default: AutonomyLevel, preferences: Mapping[str, AutonomyLevel | str] | None
) -> AutonomyLevel:
    value = preferences.get(action_category(action_type)) if preferences else None
    try:
        return AutonomyLevel(value) if value is not None else default
    except ValueError:
        return default


def _connection_reason(
    provider: ConnectionProvider | str | None,
    required_scopes: tuple[str, ...],
    connections: Iterable[Connection],
) -> PolicyReason | None:
    if provider is None:
        return None
    try:
        external_provider = ConnectionProvider(provider)
    except ValueError:
        return None
    connected = [
        connection
        for connection in connections
        if connection.provider is external_provider and connection.status is ConnectionStatus.CONNECTED
    ]
    if not connected:
        return PolicyReason.CONNECTION_MISSING
    if not any(set(required_scopes).issubset(connection.scopes) for connection in connected):
        return PolicyReason.SCOPES_MISSING
    return None


def _blocked(reason: PolicyReason, *, requires_approval: bool = False) -> PolicyDecision:
    return PolicyDecision(status=ActionStatus.BLOCKED, requires_approval=requires_approval, reason=reason)


def _approval(reason: PolicyReason) -> PolicyDecision:
    return PolicyDecision(status=ActionStatus.WAITING_APPROVAL, requires_approval=True, reason=reason)
