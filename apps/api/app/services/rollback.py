"""Safe, once-only rollback for completed reversible actions."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.repositories.connections import ConnectionRepository
from app.models.action import Action
from app.models.enums import ActionStatus
from app.models.plan import Plan
from app.models.user import User
from app.services.action_registry import ACTION_REGISTRY
from app.services.audit import AuditService
from app.services.audit_redaction import redact as _redact
from app.services.connector_registry import DEFAULT_CONNECTOR_REGISTRY, ConnectorRegistry
from app.services.plan_graph import CandidateAction
from app.services.policy_engine import PolicyEngine


class RollbackError(Exception):
    """A rollback request conflicts with the immutable action state."""


class RollbackService:
    def __init__(
        self,
        session: AsyncSession,
        connectors: ConnectorRegistry = DEFAULT_CONNECTOR_REGISTRY,
        policy: PolicyEngine | None = None,
    ) -> None:
        self._session = session
        self._connectors = connectors
        self._policy = policy or PolicyEngine()
        self._connections = ConnectionRepository(session)

    async def rollback(self, user: User, action_id: UUID) -> Action:
        action = await self._owned_action(user.id, action_id)
        if action is None:
            raise RollbackError("Action not found")
        definition = ACTION_REGISTRY.get(action.action_type)
        if not definition.reversible:
            raise RollbackError("This action is not reversible")
        if action.status is ActionStatus.ROLLED_BACK:
            raise RollbackError("Action has already been rolled back")
        if action.status is not ActionStatus.COMPLETED:
            raise RollbackError("Only completed actions can be rolled back")
        candidate = CandidateAction(
            action_key=f"rollback.{action.id.hex}",
            action_type=action.action_type,
            input=action.input,
            risk_level=action.risk_level,
            approval_mode="approval_required" if action.requires_approval else "automatic",
        )
        connections = await self._connections.list_connected(user.id)
        decision = self._policy.evaluate(candidate, user.default_autonomy, connections)
        if decision.status is ActionStatus.BLOCKED:
            raise RollbackError(f"Rollback is blocked: {decision.reason.value}")
        connector = self._connectors.get(action.connector)
        result = await connector.rollback(
            action_id=action.id, rollback_payload=action.rollback_payload
        )
        action.status = ActionStatus.ROLLED_BACK
        action.execution_result = {
            "execution": _redact(action.execution_result or {}),
            "rollback": _redact(result.output),
        }
        await AuditService(self._session).append(
            user_id=user.id,
            life_event_id=action.plan.source_event_id,
            plan_id=action.plan_id,
            action_id=action.id,
            event_name="action_rolled_back",
            actor_type="user",
            payload={"result": _redact(result.output)},
        )
        await self._session.commit()
        return action

    async def _owned_action(self, user_id: UUID, action_id: UUID) -> Action | None:
        statement = (
            select(Action)
            .join(Plan)
            .options(joinedload(Action.plan))
            .where(Action.id == action_id, Plan.user_id == user_id)
        )
        return cast(Action | None, await self._session.scalar(statement))
