"""Idempotent action execution coordinated through durable jobs."""

import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.connectors.base import ConnectorExecutionError
from app.db.repositories.connections import ConnectionRepository
from app.models.action import Action, ActionDependency
from app.models.approval import Approval
from app.models.enums import ActionStatus, ApprovalDecision, PlanStatus
from app.models.job import Job
from app.models.plan import Plan
from app.schemas.connector import ConnectorErrorCategory
from app.schemas.policy import PolicyDecision
from app.services.approvals import ApprovalService
from app.services.audit import AuditService
from app.services.audit_redaction import redact as _redact
from app.services.connector_registry import (
    DEFAULT_CONNECTOR_REGISTRY,
    ConnectorRegistry,
    ConnectorRegistryError,
)
from app.services.job_queue import JobQueue
from app.services.plan_execution import PlanExecutionService
from app.services.plan_graph import CandidateAction
from app.services.policy_engine import PolicyEngine
from app.services.retry_policy import RetryPolicy

logger = logging.getLogger(__name__)


class ActionExecutor:
    def __init__(
        self,
        session: AsyncSession,
        *,
        queue: JobQueue | None = None,
        connectors: ConnectorRegistry = DEFAULT_CONNECTOR_REGISTRY,
        policy: PolicyEngine | None = None,
        retries: RetryPolicy | None = None,
    ) -> None:
        self._session = session
        self._queue = queue or JobQueue(session)
        self._connectors = connectors
        self._policy = policy or PolicyEngine()
        self._retries = retries or RetryPolicy()
        self._connections = ConnectionRepository(session)
        self._audit_service = AuditService(session)

    async def execute(self, job: Job) -> None:
        action = await self._action(job.action_id)
        if action is None or action.plan is None:
            await self._queue.complete(job)
            return
        if action.status in (
            ActionStatus.COMPLETED,
            ActionStatus.ROLLED_BACK,
            ActionStatus.CANCELLED,
        ):
            await self._queue.complete(job)
            return
        if action.status in (ActionStatus.BLOCKED, ActionStatus.WAITING_APPROVAL):
            await self._queue.complete(job)
            return
        if not await self._dependencies_complete(action.id):
            await self._queue.schedule_retry(
                job, datetime.now(UTC), "Action dependencies are not complete"
            )
            return
        decision = await self._reevaluate(action)
        if decision.status is ActionStatus.BLOCKED:
            action.status = ActionStatus.BLOCKED
            action.policy_reason = decision.reason.value
            await self._finish_without_execution(job, action, "action_blocked")
            return
        if (
            decision.status is ActionStatus.WAITING_APPROVAL
            and action.status is not ActionStatus.APPROVED
            and not await self._was_approved(action.id)
        ):
            action.status = ActionStatus.WAITING_APPROVAL
            action.policy_reason = decision.reason.value
            await ApprovalService(self._session).create_for_actions([action])
            await self._finish_without_execution(job, action, "approval_required")
            return
        try:
            payload = self._connectors.validate_input(
                action.action_type, action.connector, action.input
            )
            connector = self._connectors.get(action.connector)
        except (ConnectorRegistryError, ValueError) as error:
            await self._fail_permanently(job, action, str(error), ConnectorErrorCategory.VALIDATION)
            return
        action.status = ActionStatus.RUNNING
        self._audit(action, "action_execution_started", {})
        await self._session.flush()
        try:
            result = await connector.execute(
                action_id=action.id, idempotency_key=action.idempotency_key, input=payload
            )
            if not await connector.verify(
                action_id=action.id, idempotency_key=action.idempotency_key, result=result
            ):
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.PERMANENT, "Connector verification failed"
                )
        except ConnectorExecutionError as error:
            await self._handle_connector_error(job, action, error)
            return
        except Exception:
            await self._handle_connector_error(
                job,
                action,
                ConnectorExecutionError(
                    ConnectorErrorCategory.RETRYABLE, "Connector execution failed"
                ),
            )
            return
        action.status = ActionStatus.COMPLETED
        action.completed_at = datetime.now(UTC)
        action.execution_result = _redact(result.output)
        action.rollback_payload = (
            _redact(result.rollback_payload) if result.rollback_payload else None
        )
        action.last_error = None
        self._audit(action, "action_completed", {"result": action.execution_result})
        await self._refresh_plan_status(action.plan)
        await self._session.flush()
        await PlanExecutionService(self._session, self._queue).queue_ready_actions(action.plan)
        await self._queue.complete(job)
        logger.info(
            "action execution completed",
            extra={
                "event_id": str(action.plan.source_event_id),
                "plan_id": str(action.plan_id),
                "action_id": str(action.id),
            },
        )

    async def _action(self, action_id: UUID | None) -> Action | None:
        if action_id is None:
            return None
        statement = (
            select(Action)
            .options(
                joinedload(Action.plan).joinedload(Plan.user),
                joinedload(Action.plan).selectinload(Plan.actions),
            )
            .where(Action.id == action_id)
        )
        return cast(Action | None, await self._session.scalar(statement))

    async def _was_approved(self, action_id: UUID) -> bool:
        return (
            await self._session.scalar(
                select(Approval.id).where(
                    Approval.action_id == action_id,
                    Approval.decision == ApprovalDecision.APPROVED,
                )
            )
        ) is not None

    async def _dependencies_complete(self, action_id: UUID) -> bool:
        statuses = await self._session.scalars(
            select(Action.status)
            .join(ActionDependency, Action.id == ActionDependency.depends_on_action_id)
            .where(ActionDependency.action_id == action_id)
        )
        return all(status is ActionStatus.COMPLETED for status in statuses)

    async def _reevaluate(self, action: Action) -> PolicyDecision:
        candidate = CandidateAction(
            action_key=str(action.id),
            action_type=action.action_type,
            input=action.input,
            connector=action.connector,  # type: ignore[arg-type]
            risk_level=action.risk_level,
            approval_mode="approval_required" if action.requires_approval else "automatic",
        )
        connections = await self._connections.list_connected(action.plan.user_id)
        return self._policy.evaluate(candidate, action.plan.user.default_autonomy, connections)

    async def _finish_without_execution(self, job: Job, action: Action, event_name: str) -> None:
        self._audit(action, event_name, {"policy_reason": action.policy_reason})
        await self._refresh_plan_status(action.plan)
        await self._queue.complete(job)

    async def _handle_connector_error(
        self, job: Job, action: Action, error: ConnectorExecutionError
    ) -> None:
        if self._retries.should_retry(error.category, job.attempts):
            action.status = ActionStatus.QUEUED
            action.last_error = error.message
            self._audit(action, "action_retry_scheduled", {"category": error.category.value})
            await self._refresh_plan_status(action.plan)
            await self._queue.schedule_retry(
                job, self._retries.next_run_at(job.idempotency_key, job.attempts), error.message
            )
            return
        await self._fail_permanently(job, action, error.message, error.category)

    async def _fail_permanently(
        self, job: Job, action: Action, error: str, category: ConnectorErrorCategory
    ) -> None:
        action.status = ActionStatus.FAILED
        action.last_error = error
        self._audit(action, "action_failed", {"category": category.value, "error": error})
        await self._refresh_plan_status(action.plan)
        await self._queue.dead_letter(job, error)

    async def _refresh_plan_status(self, plan: Plan) -> None:
        statuses = list(
            await self._session.scalars(select(Action.status).where(Action.plan_id == plan.id))
        )
        if statuses and all(
            status in (ActionStatus.COMPLETED, ActionStatus.ROLLED_BACK) for status in statuses
        ):
            plan.status = PlanStatus.COMPLETED
        elif any(status is ActionStatus.FAILED for status in statuses):
            plan.status = (
                PlanStatus.PARTIALLY_COMPLETED
                if any(status is ActionStatus.COMPLETED for status in statuses)
                else PlanStatus.FAILED
            )
        elif any(status is ActionStatus.WAITING_APPROVAL for status in statuses):
            plan.status = PlanStatus.WAITING_APPROVAL
        elif any(status in (ActionStatus.QUEUED, ActionStatus.RUNNING) for status in statuses):
            plan.status = PlanStatus.RUNNING
        elif statuses and all(status is ActionStatus.CANCELLED for status in statuses):
            plan.status = PlanStatus.CANCELLED

    def _audit(self, action: Action, event_name: str, payload: dict[str, Any]) -> None:
        self._audit_service.append_pending(
            user_id=action.plan.user_id,
            life_event_id=action.plan.source_event_id,
            plan_id=action.plan_id,
            action_id=action.id,
            event_name=event_name,
            actor_type="system",
            payload=payload,
        )
