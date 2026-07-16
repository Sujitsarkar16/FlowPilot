from app.models.enums import LifeEventType
from app.models.event import EventEntity, LifeEvent
from app.models.user import User
from tests.factories.events import life_event


def salary_event(user: User) -> LifeEvent:
    event = life_event(
        user,
        type=LifeEventType.SALARY_CREDITED,
        summary="Salary credit received",
    )
    event.entities = [
        EventEntity(kind="income", value={"amount": 5000, "currency": "usd"}, is_sensitive=True)
    ]
    return event
