import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.contracts import ActionPlan, ActionResult, LifeEvent, RawEvent

EXAMPLES = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "examples"


def load_example(name: str) -> dict[str, object]:
    with (EXAMPLES / name).open(encoding="utf-8") as example_file:
        return json.load(example_file)


def test_contract_examples_validate() -> None:
    RawEvent.model_validate(load_example("raw-event.example.json"))
    LifeEvent.model_validate(load_example("life-event.example.json"))
    ActionPlan.model_validate(load_example("action-plan.example.json"))
    ActionResult.model_validate(load_example("action-result.example.json"))


def test_unknown_action_risk_fails_validation() -> None:
    payload = load_example("action-plan.example.json")
    actions = payload["actions"]
    assert isinstance(actions, list)
    assert isinstance(actions[0], dict)
    actions[0]["risk_level"] = "purple"

    with pytest.raises(ValidationError):
        ActionPlan.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "example", "field", "value"),
    [
        (RawEvent, "raw-event.example.json", "source", "unknown_source"),
        (LifeEvent, "life-event.example.json", "type", "unknown_life_event"),
        (ActionPlan, "action-plan.example.json", "status", "unknown_plan_status"),
        (ActionResult, "action-result.example.json", "status", "unknown_result_status"),
    ],
)
def test_unknown_enum_values_fail_validation(
    model: type[RawEvent] | type[LifeEvent] | type[ActionPlan] | type[ActionResult],
    example: str,
    field: str,
    value: str,
) -> None:
    payload = load_example(example)
    payload[field] = value

    with pytest.raises(ValidationError):
        model.model_validate(payload)
