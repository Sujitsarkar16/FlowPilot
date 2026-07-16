from app.models.enums import LifeEventType
from app.models.event import EventEntity, LifeEvent
from app.models.user import User
from tests.factories.events import life_event


def client_event(user: User) -> LifeEvent:
    event = life_event(
        user,
        type=LifeEventType.CLIENT_CONFIRMED,
        summary="Acme website engagement confirmed",
    )
    event.entities = [
        EventEntity(kind="client", value={"name": "Acme"}, is_sensitive=False),
        EventEntity(kind="requirements", value={"text": "Marketing site"}, is_sensitive=False),
    ]
    return event
