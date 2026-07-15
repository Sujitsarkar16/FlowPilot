from app.models.enums import CompilationStatus
from app.models.standing_order import StandingOrder
from app.schemas.standing_order import MAX_RULE_BYTES, StandingOrderCreate


def test_standing_order_can_be_uncompiled_and_is_not_matchable() -> None:
    order = StandingOrder(
        user_id="00000000-0000-0000-0000-000000000001", instruction="Prepare trips"
    )
    assert order.compiled_rule is None
    assert not order.is_matchable


def test_only_enabled_compiled_order_is_matchable() -> None:
    order = StandingOrder(
        user_id="00000000-0000-0000-0000-000000000001",
        instruction="Prepare trips",
        compiled_rule={"trigger": "travel_booked"},
        enabled=True,
        compilation_status=CompilationStatus.COMPILED,
    )
    assert order.is_matchable


def test_compiled_rule_size_is_limited() -> None:
    oversized = {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "action_templates": [{"payload": "x" * MAX_RULE_BYTES}],
    }
    try:
        StandingOrderCreate(instruction="Prepare trips", compiled_rule=oversized)
    except ValueError as error:
        assert "safe size limit" in str(error)
    else:
        raise AssertionError("oversized compiled rule should be rejected")


def test_compiled_rule_rejects_unknown_fields() -> None:
    invalid = {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "unexpected": True,
    }
    try:
        StandingOrderCreate(instruction="Prepare trips", compiled_rule=invalid)
    except ValueError as error:
        assert "action_templates" in str(error) or "unexpected" in str(error)
    else:
        raise AssertionError("invalid compiled rule should be rejected")
