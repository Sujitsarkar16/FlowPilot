"""User-scoped approval queries with eager action context."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.action import Action
from app.models.approval import Approval
from app.models.enums import ApprovalDecision
from app.models.plan import Plan


class ApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _owned(self) -> Select[tuple[Approval]]:
        return (
            select(Approval)
            .join(Action)
            .join(Plan)
            .options(joinedload(Approval.action).joinedload(Action.plan).selectinload(Plan.actions))
        )

    async def get(self, user_id: UUID, approval_id: UUID) -> Approval | None:
        statement = self._owned().where(Approval.id == approval_id, Plan.user_id == user_id)
        return cast(Approval | None, await self.session.scalar(statement))

    async def list_pending(self, user_id: UUID, now: datetime) -> list[Approval]:
        statement = self._owned().where(
            Plan.user_id == user_id, Approval.decision.is_(None), Approval.expires_at > now
        )
        return list(
            await self.session.scalars(statement.order_by(Approval.expires_at, Approval.id))
        )

    async def list_expired(self, user_id: UUID, now: datetime) -> list[Approval]:
        statement = self._owned().where(
            Plan.user_id == user_id, Approval.decision.is_(None), Approval.expires_at <= now
        )
        return list(await self.session.scalars(statement))

    async def decide_if_pending(
        self, approval_id: UUID, decision: ApprovalDecision, user_id: UUID, now: datetime
    ) -> bool:
        result = await self.session.execute(
            update(Approval)
            .where(
                Approval.id == approval_id,
                Approval.decision.is_(None),
                Approval.expires_at > now,
            )
            .values(decision=decision, decided_at=now, decided_by_user_id=user_id)
            .execution_options(synchronize_session=False)
            .returning(Approval.id)
        )
        return result.scalar_one_or_none() is not None

    async def expire_if_pending(self, approval_id: UUID, now: datetime) -> bool:
        result = await self.session.execute(
            update(Approval)
            .where(
                Approval.id == approval_id,
                Approval.decision.is_(None),
                Approval.expires_at <= now,
            )
            .values(decision=ApprovalDecision.EXPIRED, decided_at=now)
            .execution_options(synchronize_session=False)
            .returning(Approval.id)
        )
        return result.scalar_one_or_none() is not None

    async def add(self, approval: Approval) -> Approval:
        self.session.add(approval)
        await self.session.flush()
        return approval
