from app.models.enums import LifeEventType
from app.models.event import EventEntity, LifeEvent
from app.models.user import User
from tests.factories.events import life_event


def flight_event(user: User) -> LifeEvent:
    event = life_event(
        user,
        type=LifeEventType.TRAVEL_BOOKED,
        summary="Flight AA123 to Lisbon",
    )
    event.entities = [
        EventEntity(kind="destination", value={"name": "Lisbon"}, is_sensitive=False),
        EventEntity(kind="ticket", value={"name": "AA123.pdf"}, is_sensitive=False),
    ]
    return event
