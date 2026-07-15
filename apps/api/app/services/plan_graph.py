"""Typed candidate-action DAGs with deterministic validation and ordering."""

import heapq
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TypeAlias

from app.connectors.base import ApprovalMode, ConnectorName
from app.models.enums import RiskLevel
from app.services.action_registry import ACTION_REGISTRY

MAX_PLAN_NODES = 32
MAX_PLAN_DEPTH = 8
_ACTION_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")
_RISK_ORDER = {RiskLevel.GREEN: 0, RiskLevel.YELLOW: 1, RiskLevel.RED: 2}
_APPROVAL_ORDER = {"automatic": 0, "approval_required": 1, "blocked": 2}
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


class PlanGraphError(ValueError):
    """Raised when a candidate action graph is unsafe or not a DAG."""


def _json_value(value: object, *, depth: int = 0) -> JsonValue:
    if depth > 16:
        raise PlanGraphError("action input nesting exceeds 16 levels")
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PlanGraphError("action inputs cannot contain non-finite numbers")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise PlanGraphError("action input keys must be strings")
        return {key: _json_value(value[key], depth=depth + 1) for key in sorted(value)}
    if isinstance(value, list | tuple):
        return [_json_value(item, depth=depth + 1) for item in value]
    raise PlanGraphError(f"unsupported action input value: {type(value).__name__}")


def merge_action_inputs(
    template_input: Mapping[str, object], protected_input: Mapping[str, object]
) -> dict[str, JsonValue]:
    """Merge optional template input with protected context, deterministically.

    Protected values win on conflicts so an AI-authored template cannot replace event identity
    or structured entities supplied by the application.
    """
    return _merge_objects(_json_value(template_input), _json_value(protected_input))


def _merge_objects(first: JsonValue, second: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(first, dict) or not isinstance(second, dict):
        raise PlanGraphError("action input roots must be objects")
    merged: dict[str, JsonValue] = {}
    for key in sorted(set(first) | set(second)):
        left, right = first.get(key), second.get(key)
        if isinstance(left, dict) and isinstance(right, dict):
            merged[key] = _merge_objects(left, right)
        elif key in second:
            merged[key] = right
        else:
            merged[key] = left
    return merged


@dataclass(frozen=True, slots=True)
class CandidateAction:
    """An unpersisted action node built from a registered action template."""

    action_key: str
    action_type: str
    input: Mapping[str, object] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    connector: ConnectorName | None = None
    risk_level: RiskLevel | None = None
    approval_mode: ApprovalMode | None = None
    reversible: bool | None = None

    def __post_init__(self) -> None:
        if not _ACTION_KEY.fullmatch(self.action_key):
            raise PlanGraphError("action_key must be a stable lowercase identifier")
        definition = ACTION_REGISTRY.get(self.action_type)
        if self.connector is not None and self.connector != definition.connector:
            raise PlanGraphError(
                f"{self.action_type} requires the {definition.connector} connector"
            )
        risk_level = self.risk_level or definition.default_risk
        if _RISK_ORDER[risk_level] < _RISK_ORDER[definition.minimum_risk]:
            raise PlanGraphError(f"{self.action_type} risk cannot be lowered")
        approval_mode = self.approval_mode or definition.minimum_approval
        if risk_level is RiskLevel.RED and approval_mode == "automatic":
            raise PlanGraphError("red-risk actions cannot be authorized automatically")
        if _APPROVAL_ORDER[approval_mode] < _APPROVAL_ORDER[definition.minimum_approval]:
            raise PlanGraphError(f"{self.action_type} approval cannot be relaxed")
        if self.reversible is not None and self.reversible != definition.reversible:
            raise PlanGraphError(f"{self.action_type} reversibility is registry-defined")
        dependencies = tuple(sorted(set(self.depends_on)))
        if any(not _ACTION_KEY.fullmatch(dependency) for dependency in dependencies):
            raise PlanGraphError("dependencies must be stable lowercase action keys")
        object.__setattr__(self, "input", _json_value(self.input))
        object.__setattr__(self, "depends_on", dependencies)
        object.__setattr__(self, "connector", definition.connector)
        object.__setattr__(self, "risk_level", risk_level)
        object.__setattr__(self, "approval_mode", approval_mode)
        object.__setattr__(self, "reversible", definition.reversible)

    @property
    def id(self) -> str:
        """Compatibility alias for persistence layers that call action keys IDs."""
        return self.action_key

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self.depends_on


@dataclass(frozen=True, slots=True)
class PlanGraph:
    """A bounded DAG of candidate actions with lexical Kahn ordering."""

    actions: tuple[CandidateAction, ...]
    max_nodes: int = MAX_PLAN_NODES
    max_depth: int = MAX_PLAN_DEPTH

    def __post_init__(self) -> None:
        object.__setattr__(self, "actions", tuple(self.actions))
        self.validate()

    @classmethod
    def from_actions(
        cls,
        actions: Iterable[CandidateAction],
        *,
        max_nodes: int = MAX_PLAN_NODES,
        max_depth: int = MAX_PLAN_DEPTH,
    ) -> "PlanGraph":
        return cls(tuple(actions), max_nodes=max_nodes, max_depth=max_depth)

    @property
    def action_by_key(self) -> Mapping[str, CandidateAction]:
        return {action.action_key: action for action in self.actions}

    @property
    def ordered_actions(self) -> tuple[CandidateAction, ...]:
        return self.topological_order()

    def validate(self) -> None:
        if self.max_nodes < 1 or self.max_depth < 1:
            raise PlanGraphError("max_nodes and max_depth must be positive")
        if len(self.actions) > self.max_nodes:
            raise PlanGraphError(f"plan has {len(self.actions)} nodes; maximum is {self.max_nodes}")
        keys = [action.action_key for action in self.actions]
        if len(keys) != len(set(keys)):
            raise PlanGraphError("action keys must be unique")
        nodes = self.action_by_key
        for action in self.actions:
            missing = sorted(set(action.depends_on) - nodes.keys())
            if missing:
                raise PlanGraphError(
                    f"{action.action_key} depends on unknown actions: {', '.join(missing)}"
                )
        ordered = self.topological_order()
        depths: dict[str, int] = {}
        for action in ordered:
            depths[action.action_key] = 1 + max(
                (depths[dependency] for dependency in action.depends_on), default=0
            )
        if depths and max(depths.values()) > self.max_depth:
            raise PlanGraphError(f"plan depth exceeds maximum of {self.max_depth}")

    def topological_order(self) -> tuple[CandidateAction, ...]:
        nodes = self.action_by_key
        in_degree = {key: len(action.depends_on) for key, action in nodes.items()}
        successors: dict[str, list[str]] = {key: [] for key in nodes}
        for action in nodes.values():
            for dependency in action.depends_on:
                if dependency in successors:
                    successors[dependency].append(action.action_key)
        ready = [key for key, degree in in_degree.items() if degree == 0]
        heapq.heapify(ready)
        ordered: list[CandidateAction] = []
        while ready:
            key = heapq.heappop(ready)
            ordered.append(nodes[key])
            for successor in sorted(successors[key]):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    heapq.heappush(ready, successor)
        if len(ordered) != len(nodes):
            raise PlanGraphError("plan contains a dependency cycle")
        return tuple(ordered)


def validate_plan_graph(
    actions: Iterable[CandidateAction],
    *,
    max_nodes: int = MAX_PLAN_NODES,
    max_depth: int = MAX_PLAN_DEPTH,
) -> PlanGraph:
    """Construct and validate a graph for callers that only have action iterables."""
    return PlanGraph.from_actions(actions, max_nodes=max_nodes, max_depth=max_depth)
