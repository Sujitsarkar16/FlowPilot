import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import MockConnector
from app.models.audit import AuditEntry
from app.models.enums import ActionStatus, ApprovalDecision, PlanStatus, RiskLevel
from app.models.job import Job
from app.schemas.connector import ConnectorErrorCategory
from app.services.action_executor import ActionExecutor
from app.services.approvals import ApprovalService
from app.services.connector_registry import ConnectorRegistry
from app.services.plan_execution import PlanExecutionService
from app.services.rollback import RollbackService
from tests.factories import action, connection, plan, user
from tests.fixtures import flight_event


@pytest.mark.asyncio
async def test_travel_approval_executes_with_a_fake_connector_and_audit(
    session: AsyncSession,
) -> None:
    actor = user()
    event = flight_event(actor)
    workflow = plan(actor, event, status=PlanStatus.WAITING_APPROVAL)
    message = action(workflow)
    telegram = connection(actor)
    session.add_all([actor, event, workflow, message, telegram])
    await session.flush()
    pending = (await ApprovalService(session).create_for_actions([message]))[0]
    await session.commit()
    await ApprovalService(session).decide(actor, pending.id, ApprovalDecision.APPROVED)
    job = (await session.scalars(select(Job))).one()
    fake = MockConnector("telegram")
    await ActionExecutor(session, connectors=ConnectorRegistry((fake,))).execute(job)
    await session.refresh(message)
    names = list(
        await session.scalars(select(AuditEntry.event_name).where(AuditEntry.action_id == message.id))
    )
    assert message.status is ActionStatus.COMPLETED, message.last_error
    assert len(fake.executions) == 1
    assert {"approval_requested", "approval_approved", "action_completed"} <= set(names)


@pytest.mark.asyncio
async def test_retry_then_rollback_preserves_auditable_final_state(
    session: AsyncSession,
) -> None:
    actor = user()
    event = flight_event(actor)
    workflow = plan(actor, event)
    document = action(
        workflow,
        action_type="travel.generate_documents",
        connector="internal",
        input={"checklist_title": "Pack", "event_id": str(event.id), "event_type": "travel_booked"},
        status=ActionStatus.PLANNED,
        risk_level=RiskLevel.GREEN,
        requires_approval=False,
    )
    session.add_all([actor, event, workflow, document])
    await session.commit()
    await PlanExecutionService(session).execute(actor, workflow.id)
    job = (await session.scalars(select(Job))).one()
    internal = MockConnector("internal", (ConnectorErrorCategory.RETRYABLE, None))
    registry = ConnectorRegistry((internal,))
    executor = ActionExecutor(session, connectors=registry)
    await executor.execute(job)
    await executor.execute(job)
    await session.refresh(document)
    rolled_back = await RollbackService(session, connectors=registry).rollback(actor, document.id)
    names = list(
        await session.scalars(select(AuditEntry.event_name).where(AuditEntry.action_id == document.id))
    )
    assert rolled_back.status is ActionStatus.ROLLED_BACK
    assert len(internal.executions) == 1 and len(internal.rollbacks) == 1
    assert {"action_retry_scheduled", "action_completed", "action_rolled_back"} <= set(names)
