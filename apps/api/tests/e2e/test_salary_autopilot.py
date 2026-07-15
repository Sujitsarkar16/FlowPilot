from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes import mock_bank
from app.api.routes.mock_bank import calculate_allocations, router
from app.core.config import Settings
from app.db.session import get_session
from app.models.enums import CompilationStatus
from app.models.standing_order import StandingOrder
from app.models.user import User
from app.services.action_registry import ACTION_REGISTRY


def _rule() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "trigger_event_types": ["salary_credited"],
        "entity_conditions": [],
        "action_templates": [
            {
                "action_type": "salary.update_budget",
                "connector": "internal",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            },
            {
                "action_type": "salary.propose_transfer",
                "connector": "mock_bank",
                "input": {},
                "risk_level": "red",
                "approval_mode": "approval_required",
            },
        ],
        "explanation": "Allocate each salary credit.",
    }


@pytest.mark.asyncio
async def test_salary_webhook_creates_an_idempotent_safe_plan(
    session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        mock_bank, "get_settings", lambda: Settings(mock_bank_webhook_secret="secret")
    )
    user = User(auth_subject="salary-user")
    session.add(user)
    await session.flush()
    session.add(
        StandingOrder(
            user_id=user.id,
            instruction="Allocate salary.",
            compiled_rule=_rule(),
            enabled=True,
            compilation_status=CompilationStatus.COMPILED,
        )
    )
    await session.commit()

    async def override_session() -> AsyncIterator[object]:
        yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = override_session
    payload = {
        "user_id": str(user.id),
        "transaction_id": "salary-001",
        "amount": 5000,
        "currency": "usd",
        "occurred_at": datetime(2026, 7, 15, tzinfo=UTC).isoformat(),
        "month_spend": 2200,
        "rent_rate": 0.3,
        "savings_rate": 0.2,
        "investment_rate": 0.1,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/mock-bank/salary-credits",
            json=payload,
            headers={"X-Mock-Bank-Secret": "secret"},
        )
        replay = await client.post(
            "/api/v1/mock-bank/salary-credits",
            json=payload,
            headers={"X-Mock-Bank-Secret": "secret"},
        )

    assert created.status_code == 201
    assert created.json()["plan_id"]
    assert created.json()["allocations"] == {
        "rent": 1500.0,
        "savings": 1000.0,
        "investment": 500.0,
        "discretionary": 2000.0,
        "month_spend": 2200.0,
        "income": 5000.0,
    }
    assert created.json()["overspending_warning"]
    assert replay.json()["is_duplicate"] is True


def test_salary_allocation_rounds_down_and_transfer_stays_approval_only() -> None:
    payload = mock_bank.SalaryCreditWebhook(
        user_id="00000000-0000-0000-0000-000000000001",
        transaction_id="salary-002",
        amount=1,
        currency="usd",
        occurred_at=datetime(2026, 7, 15, tzinfo=UTC),
        rent_rate=0.333,
        savings_rate=0.333,
        investment_rate=0.333,
    )
    allocations, warning = calculate_allocations(payload)

    assert allocations == {
        "rent": 0.33,
        "savings": 0.33,
        "investment": 0.33,
        "discretionary": 0.01,
        "month_spend": 0.0,
        "income": 1.0,
    }
    assert warning is None
    assert ACTION_REGISTRY.get("salary.propose_transfer").minimum_approval == "approval_required"
