import pytest

from app.services.plan_graph import (
    CandidateAction,
    PlanGraph,
    PlanGraphError,
    merge_action_inputs,
)


def action(key: str, dependencies: tuple[str, ...] = ()) -> CandidateAction:
    return CandidateAction(key, "travel.get_weather", depends_on=dependencies)


def test_graph_orders_lexically_and_merges_protected_context() -> None:
    graph = PlanGraph.from_actions(
        [
            action("travel.weather"),
            action("travel.folder"),
            action("travel.checklist", ("travel.folder",)),
        ]
    )

    assert [item.action_key for item in graph.ordered_actions] == [
        "travel.folder",
        "travel.checklist",
        "travel.weather",
    ]
    assert merge_action_inputs(
        {"event_id": "spoof", "nested": {"a": 1}}, {"event_id": "real", "nested": {"b": 2}}
    ) == {"event_id": "real", "nested": {"a": 1, "b": 2}}


def test_graph_rejects_missing_dependencies_cycles_and_depth() -> None:
    with pytest.raises(PlanGraphError, match="unknown actions"):
        PlanGraph.from_actions([action("travel.weather", ("travel.missing",))])
    with pytest.raises(PlanGraphError, match="cycle"):
        PlanGraph.from_actions(
            [action("travel.a", ("travel.b",)), action("travel.b", ("travel.a",))]
        )
    with pytest.raises(PlanGraphError, match="depth"):
        PlanGraph.from_actions([action("travel.a"), action("travel.b", ("travel.a",))], max_depth=1)
