"""Post-ingestion interpretation: classify → extract entities → plan.

Shared by Gmail sync and other automatic sources so raw events become visible
life events and (when a standing order matches) policy-checked plans.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.events import EventRepository
from app.db.repositories.users import UserRepository
from app.models.event import LifeEvent, RawEvent
from app.models.plan import Plan
from app.models.user import User
from app.services.ai.base import AIProvider
from app.services.entity_extractor import EntityExtractor
from app.services.event_classifier import EventClassifier
from app.services.plan_customizer import PlanCustomizer
from app.services.planning import NoMatchingStandingOrderError, PlanningService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    life_event: LifeEvent | None
    plan: Plan | None
    already_processed: bool


class EventPipelineService:
    """Idempotent classify → extract → optional plan for one raw event."""

    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._session = session
        self._provider = provider
        self._events = EventRepository(session)

    async def process_raw_event(
        self, raw_event: RawEvent, user: User | None = None
    ) -> PipelineResult:
        """Interpret a raw event once; safe to call again after partial failure."""
        owner = user or await UserRepository(self._session).get(raw_event.user_id)
        if owner is None:
            logger.warning(
                "event pipeline skipped: user missing",
                extra={"raw_event_id": str(raw_event.id), "user_id": str(raw_event.user_id)},
            )
            return PipelineResult(None, None, already_processed=False)

        existing = await self._events.get_life_by_raw(owner.id, raw_event.id)
        if existing is not None:
            plan = await self._maybe_plan(owner, existing.id)
            return PipelineResult(existing, plan, already_processed=True)

        outcome = await EventClassifier(self._session, self._provider).classify(raw_event)
        await EntityExtractor(self._session, self._provider).extract(
            outcome.life_event, outcome.sanitized.text
        )
        plan = await self._maybe_plan(owner, outcome.life_event.id)
        return PipelineResult(outcome.life_event, plan, already_processed=False)

    async def _maybe_plan(self, user: User, life_event_id: UUID) -> Plan | None:
        try:
            return await PlanningService(self._session, PlanCustomizer(self._provider)).create(
                user, life_event_id
            )
        except NoMatchingStandingOrderError:
            return None
