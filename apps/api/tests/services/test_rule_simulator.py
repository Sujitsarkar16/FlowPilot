import pytest
from sqlalchemy import func, select

from app.models.action import Action
from app.models.enums import CompilationStatus
from app.models.job import Job
from app.models.plan import Plan
from app.models.standing_order import StandingOrder
from app.models.user import User
from app.schemas.standing_order import StandingOrderSimulationInput
from app.services.ai.fake_provider import FakeAIProvider
from app.services.rule_simulator import RuleSimulator
from app.services.standing_order_compiler import StandingOrderCompiler
from app.services.standing_orders import StandingOrderService


def responder(system: str, user: str, schema: type) -> dict[str, object]:
    if schema.__name__ == "Classification":
        event_type = "travel_booked" if "flight" in user.lower() else "client_opportunity"
        return {"type": event_type, "confidence": 0.9, "importance": "high", "summary": "Sample"}
    return {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "entity_conditions": [],
        "action_templates": [
            {
                "action_type": "travel.create_folder",
                "connector": "google",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            }
        ],
        "explanation": "Prepare travel.",
    }


@pytest.mark.asyncio
async def test_simulation_matches_only_travel_and_does_not_create_execution_rows(
    session: object,
) -> None:
    user = User(auth_subject="simulator-user")
    session.add(user)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    compiler = StandingOrderCompiler(FakeAIProvider(responder))
    rule = (await compiler.compile("Prepare travel")).rule
    order = StandingOrder(
        user_id=user.id,
        instruction="Prepare travel",
        enabled=True,
        compilation_status=CompilationStatus.COMPILED,
        compiled_rule=rule.model_dump(mode="json"),
    )
    session.add(order)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    service = StandingOrderService(session, compiler, RuleSimulator(FakeAIProvider(responder)))  # type: ignore[arg-type]

    travel = await service.simulate(
        user.id, order.id, StandingOrderSimulationInput(sample_event="Flight booked")
    )
    client = await service.simulate(
        user.id, order.id, StandingOrderSimulationInput(sample_event="New client")
    )

    assert travel.matched and travel.proposed_actions
    assert not client.matched
    for model in (Plan, Action, Job):
        assert await session.scalar(select(func.count()).select_from(model)) == 0  # type: ignore[attr-defined]
