import pytest

from app.connectors.base import ActionDefinition, InputField
from app.models.enums import RiskLevel
from app.services.action_registry import ACTION_REGISTRY, ActionRegistry, ActionRegistryError


def test_catalog_contains_all_supported_actions_and_safe_metadata() -> None:
    metadata = ACTION_REGISTRY.frontend_metadata()

    assert len(metadata) == 14
    assert [item["action_type"] for item in metadata] == sorted(
        item["action_type"] for item in metadata
    )
    assert all(item["default_risk"] and item["input_schema"] for item in metadata)
    with pytest.raises(ActionRegistryError, match="unknown action type"):
        ACTION_REGISTRY.get("unknown.action")


def test_duplicate_registration_is_rejected() -> None:
    definition = ActionDefinition(
        action_type="test.action",
        connector="internal",
        default_risk=RiskLevel.GREEN,
        minimum_risk=RiskLevel.GREEN,
        reversible=True,
        required_scopes=(),
        provider="internal",
        input_schema={"event_id": InputField("string", True)},
        minimum_approval="automatic",
    )
    registry = ActionRegistry((definition,))

    with pytest.raises(ActionRegistryError, match="duplicate action registration"):
        registry.register(definition)
