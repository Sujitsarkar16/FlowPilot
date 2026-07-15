"""Extract and persist validated entities for a life event."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventEntity, LifeEvent
from app.schemas.entities import ExtractedEntities
from app.services.ai.base import AIProvider
from app.services.ai.prompts.extract_entities import build_entity_prompt
from app.services.ai.prompts.system import SYSTEM_PROMPT
from app.services.ai.schemas import AIError


class EntityExtractor:
    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._session = session
        self._provider = provider

    async def extract(self, life_event: LifeEvent, content: str) -> list[EventEntity]:
        """Run extraction, persist entities, and return them.

        AI failure yields zero entities rather than aborting the pipeline.
        """
        try:
            result = await self._provider.generate_structured(
                system=SYSTEM_PROMPT,
                user=build_entity_prompt(life_event.type.value, content),
                schema=ExtractedEntities,
            )
            extracted = result.data
        except AIError:
            extracted = ExtractedEntities()

        entities = [
            EventEntity(
                life_event_id=life_event.id,
                kind=item.kind,
                value=item.value,
                is_sensitive=item.is_sensitive,
            )
            for item in extracted.entities
        ]
        if entities:
            self._session.add_all(entities)
            await self._session.commit()
        return entities
