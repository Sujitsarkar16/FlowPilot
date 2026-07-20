"""Safely customize only registered optional action inputs."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr

from app.connectors.base import InputField
from app.services.action_registry import ACTION_REGISTRY, ActionRegistry
from app.services.ai.base import AIProvider
from app.services.ai.prompts.customize_plan import build_customize_plan_prompt
from app.services.ai.prompts.system import SYSTEM_PROMPT
from app.services.ai.schemas import AIError
from app.services.plan_graph import CandidateAction, PlanGraph, PlanGraphError

Scalar = StrictStr | StrictInt | StrictFloat | StrictBool
logger = logging.getLogger(__name__)
_NO_PROVIDER_RATIONALE = (
    "AI plan customization is not configured; the original validated plan is retained."
)
_INVALID_RESPONSE_RATIONALE = (
    "AI plan customization returned an invalid response; the original validated plan is retained."
)
_UNEXPECTED_FAILURE_RATIONALE = (
    "AI plan customization failed unexpectedly; the original validated plan is retained."
)


class PlanCustomizationOutput(BaseModel):
    """The complete, strict AI output contract for an input-only customization."""

    model_config = ConfigDict(extra="forbid", strict=True)

    rationale: str = Field(min_length=1, max_length=1_000)
    overrides: dict[str, dict[str, Scalar]] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlanCustomizationResult:
    graph: PlanGraph
    rationale: str
    used_fallback: bool = False


class PlanCustomizer:
    """Apply a structured AI suggestion without allowing graph structure changes."""

    def __init__(
        self, provider: AIProvider | None = None, registry: ActionRegistry = ACTION_REGISTRY
    ) -> None:
        self._provider = provider
        self._registry = registry

    async def customize(self, graph: PlanGraph) -> PlanCustomizationResult:
        graph.validate()
        if self._provider is None:
            return self._fallback(graph, _NO_PROVIDER_RATIONALE)
        safe_fields = self._safe_fields(graph)
        try:
            response = await self._provider.generate_structured(
                system=SYSTEM_PROMPT,
                user=build_customize_plan_prompt(graph, safe_fields),
                schema=PlanCustomizationOutput,
            )
            actions = self._apply_overrides(graph, response.data.overrides, safe_fields)
            customized = PlanGraph.from_actions(
                actions, max_nodes=graph.max_nodes, max_depth=graph.max_depth
            )
            customized.validate()
        except (AIError, PlanGraphError, TypeError, ValueError) as error:
            logger.warning(
                "plan customization response rejected",
                extra={"error_type": type(error).__name__},
            )
            return self._fallback(graph, _INVALID_RESPONSE_RATIONALE)
        except Exception:
            logger.exception("plan customization failed unexpectedly")
            return self._fallback(graph, _UNEXPECTED_FAILURE_RATIONALE)
        return PlanCustomizationResult(customized, response.data.rationale)

    @staticmethod
    def _fallback(graph: PlanGraph, rationale: str) -> PlanCustomizationResult:
        return _fallback(graph, rationale)

    def _safe_fields(self, graph: PlanGraph) -> dict[str, tuple[str, ...]]:
        return {
            action.action_key: tuple(
                name
                for name, field in self._registry.get(action.action_type).input_schema.items()
                if not field.required and field.value_type in {"string", "number", "boolean"}
            )
            for action in graph.actions
        }

    def _apply_overrides(
        self,
        graph: PlanGraph,
        overrides: Mapping[str, Mapping[str, Scalar]],
        safe_fields: Mapping[str, tuple[str, ...]],
    ) -> tuple[CandidateAction, ...]:
        if unknown_keys := set(overrides) - set(graph.action_by_key):
            raise PlanGraphError(f"overrides reference unknown actions: {sorted(unknown_keys)}")
        updated: list[CandidateAction] = []
        for action in graph.actions:
            values = overrides.get(action.action_key, {})
            definition = self._registry.get(action.action_type)
            input_data = dict(action.input)
            for name, value in values.items():
                if name not in safe_fields[action.action_key]:
                    raise PlanGraphError(f"{action.action_key} cannot override {name}")
                if not _matches_field(value, definition.input_schema[name]):
                    raise PlanGraphError(f"{action.action_key}.{name} has an invalid scalar type")
                input_data[name] = value
            updated.append(_replace_input(action, input_data))
        return tuple(updated)


def _matches_field(value: object, field: InputField) -> bool:
    if field.value_type == "string":
        return isinstance(value, str)
    if field.value_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if field.value_type == "boolean":
        return isinstance(value, bool)
    return False


def _replace_input(action: CandidateAction, input_data: Mapping[str, object]) -> CandidateAction:
    """Recreate one immutable node while preserving every non-input graph field."""
    return CandidateAction(
        action_key=action.action_key,
        action_type=action.action_type,
        input=input_data,
        depends_on=action.depends_on,
        connector=action.connector,
        risk_level=action.risk_level,
        approval_mode=action.approval_mode,
        reversible=action.reversible,
    )


def _fallback(graph: PlanGraph, rationale: str) -> PlanCustomizationResult:
    return PlanCustomizationResult(graph, rationale, used_fallback=True)
