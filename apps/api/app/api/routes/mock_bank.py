"""Secret-protected simulated salary-credit intake; it never transfers funds."""

from decimal import ROUND_DOWN, Decimal
from secrets import compare_digest
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.repositories.events import EventRepository
from app.db.repositories.plans import PlanRepository
from app.db.repositories.users import UserRepository
from app.db.session import get_session
from app.models.enums import Importance, LifeEventType, RawEventStatus
from app.models.event import EventEntity, LifeEvent
from app.schemas.raw_sources import MockBankSource
from app.services.event_ingestion import EventIngestionService
from app.services.event_normalizer import normalize
from app.services.planning import NoMatchingStandingOrderError, PlanningService

router = APIRouter(prefix="/api/v1/mock-bank", tags=["mock-bank"])
_CENTS = Decimal("0.01")


class SalaryCreditWebhook(MockBankSource):
    """Validated simulation payload; the shared secret is the authentication boundary."""

    user_id: UUID
    amount: float = Field(gt=0)
    month_spend: float = Field(default=0, ge=0)
    rent_rate: float = Field(default=0.30, ge=0, le=1)
    savings_rate: float = Field(default=0.20, ge=0, le=1)
    investment_rate: float = Field(default=0.10, ge=0, le=1)

    @model_validator(mode="after")
    def rates_fit_income(self) -> "SalaryCreditWebhook":
        if self.rent_rate + self.savings_rate + self.investment_rate > 1:
            raise ValueError("allocation rates cannot exceed income")
        return self


class SalaryCreditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    plan_id: UUID | None
    is_duplicate: bool
    allocations: dict[str, float]
    overspending_warning: str | None


def calculate_allocations(payload: SalaryCreditWebhook) -> tuple[dict[str, float], str | None]:
    """Allocate whole cents deterministically so a mock plan cannot over-allocate income."""
    income = Decimal(str(payload.amount)).quantize(_CENTS, rounding=ROUND_DOWN)
    rates = {
        "rent": payload.rent_rate,
        "savings": payload.savings_rate,
        "investment": payload.investment_rate,
    }
    allocations = {
        category: (income * Decimal(str(rate))).quantize(_CENTS, rounding=ROUND_DOWN)
        for category, rate in rates.items()
    }
    discretionary = income - sum(allocations.values())
    spent = Decimal(str(payload.month_spend)).quantize(_CENTS, rounding=ROUND_DOWN)
    warning = (
        "Mock monthly spending exceeds the remaining discretionary budget."
        if spent > discretionary
        else None
    )
    return (
        {
            **{category: float(amount) for category, amount in allocations.items()},
            "discretionary": float(discretionary),
            "month_spend": float(spent),
            "income": float(income),
        },
        warning,
    )


@router.post(
    "/salary-credits", response_model=SalaryCreditResponse, status_code=status.HTTP_201_CREATED
)
async def receive_salary_credit(
    payload: SalaryCreditWebhook,
    x_mock_bank_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> SalaryCreditResponse:
    """Persist one trusted mock salary event and plan it through the normal policy path."""
    settings: Settings = get_settings()
    expected = settings.mock_bank_webhook_secret
    if expected is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mock bank is disabled"
        )
    if not x_mock_bank_secret or not compare_digest(
        x_mock_bank_secret, expected.get_secret_value()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid mock bank secret"
        )
    user = await UserRepository(session).get(payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    source = MockBankSource(
        transaction_id=payload.transaction_id,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        occurred_at=payload.occurred_at,
    )
    ingestion = await EventIngestionService(session).ingest(
        user.id, normalize(source), idempotency_key=payload.transaction_id
    )
    events = EventRepository(session)
    if ingestion.is_duplicate:
        event = await events.get_life_by_raw(user.id, ingestion.raw_event.id)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Salary event is still processing"
            )
        plan = await PlanRepository(session).latest_for_event(user.id, event.id)
        allocations, warning = calculate_allocations(payload)
        return SalaryCreditResponse(
            event_id=event.id,
            plan_id=plan.id if plan else None,
            is_duplicate=True,
            allocations=allocations,
            overspending_warning=warning,
        )

    allocations, warning = calculate_allocations(payload)
    event = LifeEvent(
        user_id=user.id,
        raw_event_id=ingestion.raw_event.id,
        type=LifeEventType.SALARY_CREDITED,
        confidence=1,
        importance=Importance.MEDIUM,
        summary=f"Salary credit: {payload.currency.upper()} {allocations['income']:.2f}",
        occurred_at=ingestion.raw_event.received_at,
    )
    event.entities.append(
        EventEntity(
            kind="salary",
            value={
                "currency": payload.currency.upper(),
                **allocations,
                "overspending_warning": warning or "",
            },
            is_sensitive=True,
        )
    )
    ingestion.raw_event.status = RawEventStatus.NORMALIZED
    session.add(event)
    await session.commit()

    try:
        plan = await PlanningService(session).create(user, event.id)
    except NoMatchingStandingOrderError:
        plan = None
    return SalaryCreditResponse(
        event_id=event.id,
        plan_id=plan.id if plan else None,
        is_duplicate=False,
        allocations=allocations,
        overspending_warning=warning,
    )
