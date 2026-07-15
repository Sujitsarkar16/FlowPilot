"""Classify raw events into persisted life events.

Classification never triggers an action. It only produces and stores an interpretation;
downstream planning is a separate, explicit step.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Importance, LifeEventType, RawEventStatus
from app.models.event import LifeEvent, RawEvent
from app.schemas.classification import Classification
from app.services.ai.base import AIProvider
from app.services.ai.prompts.classify_event import build_classification_prompt
from app.services.ai.prompts.system import SYSTEM_PROMPT
from app.services.ai.schemas import AIError
from app.services.audit import AuditService
from app.services.content_safety import SanitizedContent, sanitize_untrusted_content

# Below this confidence we downgrade to a safe, generic interpretation.
_LOW_CONFIDENCE = 0.5


@dataclass(frozen=True)
class ClassificationOutcome:
    life_event: LifeEvent
    classification: Classification
    sanitized: SanitizedContent


class EventClassifier:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._session = session
        self._provider = provider

    async def classify(self, raw_event: RawEvent) -> ClassificationOutcome:
        payload = raw_event.payload
        metadata = payload.get("trusted_metadata", {}) if isinstance(payload, dict) else {}
        content = payload.get("untrusted_content", "") if isinstance(payload, dict) else ""
        sanitized = sanitize_untrusted_content(str(content))

        prompt = build_classification_prompt(raw_event.event_type, metadata, sanitized.text)
        try:
            result = await self._provider.generate_structured(
                system=SYSTEM_PROMPT, user=prompt, schema=Classification
            )
            classification = result.data
        except AIError:
            # Never fail the event; fall back to a safe, non-actionable interpretation.
            classification = Classification(
                type=LifeEventType.GENERIC_IMPORTANT_EVENT,
                confidence=0.0,
                importance=Importance.MEDIUM,
                summary=f"Unclassified {raw_event.event_type} event",
                reason="AI classification unavailable",
            )

        if classification.confidence < _LOW_CONFIDENCE:
            classification = classification.model_copy(
                update={"type": LifeEventType.GENERIC_IMPORTANT_EVENT}
            )

        life_event = LifeEvent(
            user_id=raw_event.user_id,
            raw_event_id=raw_event.id,
            type=classification.type,
            confidence=classification.confidence,
            importance=classification.importance,
            summary=classification.summary,
            occurred_at=raw_event.received_at,
        )
        self._session.add(life_event)
        raw_event.status = RawEventStatus.NORMALIZED
        await self._session.flush()
        await AuditService(self._session).append(
            user_id=raw_event.user_id,
            life_event_id=life_event.id,
            event_name="event_classified",
            actor_type="system",
            payload={
                "type": classification.type.value,
                "confidence": classification.confidence,
                "importance": classification.importance.value,
            },
        )
        await self._session.commit()
        await self._session.refresh(life_event)
        return ClassificationOutcome(life_event, classification, sanitized)
