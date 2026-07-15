from uuid import uuid4

import pytest

from app.models.connection import Connection
from app.models.enums import (
    ActionStatus,
    AutonomyLevel,
    ConnectionProvider,
    ConnectionStatus,
)
from app.schemas.policy import PolicyReason
from app.services.plan_graph import CandidateAction
from app.services.policy_engine import PolicyEngine


def connection(provider: ConnectionProvider, scopes: list[str]) -> Connection:
    return Connection(
        user_id=uuid4(),
        provider=provider,
        provider_account_id="account",
        status=ConnectionStatus.CONNECTED,
        scopes=scopes,
    )


def test_policy_blocks_missing_connections_and_scopes_before_risk() -> None:
    action = CandidateAction("salary.transfer", "salary.propose_transfer")
    engine = PolicyEngine()

    missing = engine.evaluate(action, AutonomyLevel.SAFE_ACTIONS, [])
    insufficient = engine.evaluate(
        action,
        AutonomyLevel.SAFE_ACTIONS,
        [connection(ConnectionProvider.MOCK_BANK, [])],
    )

    assert (missing.status, missing.reason) == (
        ActionStatus.BLOCKED,
        PolicyReason.CONNECTION_MISSING,
    )
    assert (insufficient.status, insufficient.reason) == (
        ActionStatus.BLOCKED,
        PolicyReason.SCOPES_MISSING,
    )


def test_policy_red_actions_wait_for_approval_when_connection_is_ready() -> None:
    decision = PolicyEngine().evaluate(
        CandidateAction("salary.transfer", "salary.propose_transfer"),
        AutonomyLevel.SAFE_ACTIONS,
        [connection(ConnectionProvider.MOCK_BANK, ["transfers:write"])],
    )

    assert decision.status is ActionStatus.WAITING_APPROVAL
    assert decision.requires_approval
    assert decision.reason is PolicyReason.RED_REQUIRES_APPROVAL


def test_policy_blocks_explicit_template_mode() -> None:
    decision = PolicyEngine().evaluate(
        CandidateAction("travel.weather", "travel.get_weather"),
        AutonomyLevel.SAFE_ACTIONS,
        [],
        template_mode="blocked",
    )

    assert decision.status is ActionStatus.BLOCKED
    assert decision.reason is PolicyReason.TEMPLATE_BLOCKED


@pytest.mark.parametrize(
    ("autonomy", "status", "reason"),
    [
        (AutonomyLevel.SAFE_ACTIONS, ActionStatus.PLANNED, PolicyReason.SAFE_AUTOMATIC),
        (AutonomyLevel.SUGGEST, ActionStatus.PLANNED, PolicyReason.SUGGEST_MANUAL),
        (AutonomyLevel.OBSERVE, ActionStatus.PLANNED, PolicyReason.OBSERVE_MANUAL),
    ],
)
def test_internal_and_weather_actions_need_no_connection(
    autonomy: AutonomyLevel, status: ActionStatus, reason: PolicyReason
) -> None:
    decision = PolicyEngine().evaluate(
        CandidateAction("travel.weather", "travel.get_weather"), autonomy, []
    )

    assert (decision.status, decision.requires_approval, decision.reason) == (status, False, reason)


def test_policy_honors_registry_required_approval() -> None:
    decision = PolicyEngine().evaluate(
        CandidateAction("travel.notify", "travel.notify_family"),
        AutonomyLevel.SAFE_ACTIONS,
        [connection(ConnectionProvider.TELEGRAM, ["bot.send_messages"])],
    )

    assert decision.status is ActionStatus.WAITING_APPROVAL
    assert decision.requires_approval
    assert decision.reason is PolicyReason.ACTION_REQUIRES_APPROVAL


def test_policy_keeps_red_approval_requirement_when_connection_is_missing() -> None:
    decision = PolicyEngine().evaluate(
        CandidateAction("salary.transfer", "salary.propose_transfer"),
        AutonomyLevel.SAFE_ACTIONS,
        [],
    )

    assert (decision.status, decision.requires_approval, decision.reason) == (
        ActionStatus.BLOCKED,
        True,
        PolicyReason.CONNECTION_MISSING,
    )
