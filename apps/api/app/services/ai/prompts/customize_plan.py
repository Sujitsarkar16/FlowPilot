"""Prompt construction for bounded, input-only plan customization."""

import json
from collections.abc import Mapping

from app.services.ai.prompts.system import wrap_untrusted
from app.services.plan_graph import PlanGraph


def build_customize_plan_prompt(
    graph: PlanGraph, safe_fields: Mapping[str, tuple[str, ...]]
) -> str:
    """Describe the plan as data and expose only permitted override names."""
    payload = {
        "actions": [
            {
                "action_key": action.action_key,
                "action_type": action.action_type,
                "input": action.input,
                "safe_optional_fields": list(safe_fields[action.action_key]),
            }
            for action in graph.ordered_actions
        ]
    }
    return (
        "Customize only optional scalar input values for the existing actions in the supplied "
        "plan. Return the requested JSON schema with a concise rationale and overrides keyed "
        "only by an existing action_key. Never add actions or change action types, connectors, "
        "risks, approvals, dependencies, or any field not listed in safe_optional_fields. "
        "Use an empty overrides object when no safe improvement is needed.\n"
        f"{wrap_untrusted(json.dumps(payload, sort_keys=True, separators=(',', ':')))}"
    )
