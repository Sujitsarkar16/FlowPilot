"""Non-persisting standing-order evaluation for user-supplied examples."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.models.enums import Importance, LifeEventType
from app.schemas.classification import Classification
from app.schemas.compiled_rule import ActionTemplate, CompiledRule, EntityCondition
from app.services.ai.base import AIProvider
from app.services.ai.prompts.classify_event import build_classification_prompt
from app.services.ai.prompts.system import SYSTEM_PROMPT
from app.services.ai.schemas import AIError
from app.services.content_safety import sanitize_untrusted_content

_LOW_CONFIDENCE = 0.5


@dataclass(frozen=True)
class SimulationResult:
    event_type: LifeEventType
    matched: bool
    proposed_actions: list[ActionTemplate]
    warnings: list[str]


class RuleSimulator:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def simulate(self, rule: CompiledRule, sample_event: str) -> SimulationResult:
        sanitized = sanitize_untrusted_content(sample_event)
        warnings = [*sanitized.injection_warnings]
        classification = await self._classify(sanitized.text)
        matched = classification.type in rule.trigger_event_types and self._conditions_match(
            rule.entity_conditions, ()
        )
        if not matched:
            warnings.append("The sample did not satisfy this rule's trigger or entity conditions.")
        return SimulationResult(
            event_type=classification.type,
            matched=matched,
            proposed_actions=list(rule.action_templates) if matched else [],
            warnings=warnings,
        )

    async def _classify(self, text: str) -> Classification:
        try:
            result = await self._provider.generate_structured(
                system=SYSTEM_PROMPT,
                user=build_classification_prompt("standing-order simulation", {}, text),
                schema=Classification,
            )
            classification = result.data
        except AIError:
            return Classification(
                type=LifeEventType.GENERIC_IMPORTANT_EVENT,
                confidence=0.0,
                importance=Importance.MEDIUM,
                summary="Unclassified simulation event",
                reason="AI classification unavailable",
            )
        if classification.confidence < _LOW_CONFIDENCE:
            return classification.model_copy(update={"type": LifeEventType.GENERIC_IMPORTANT_EVENT})
        return classification

    @staticmethod
    def _conditions_match(
        conditions: Iterable[EntityCondition], entities: Iterable[dict[str, Any]]
    ) -> bool:
        # Simulation intentionally has no persisted entity extraction yet. Empty conditions match;
        # a conditional rule remains conservative until the real event entity pipeline evaluates it.
        return not list(conditions) and not list(entities)
