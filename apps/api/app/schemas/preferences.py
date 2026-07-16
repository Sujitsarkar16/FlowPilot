"""Validated, persisted user autonomy preferences."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AutonomyLevel
from app.models.user import User

PREFERENCE_CATEGORIES = frozenset({"travel", "calendar", "messages", "subscriptions"})
FIXED_RESTRICTIONS = (
    "High-risk actions always require approval.",
    "Money movement can never be enabled automatically.",
    "External messages retain their action-level approval requirement.",
)


class PreferencesRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    autonomy_level: AutonomyLevel
    category_behaviors: dict[str, AutonomyLevel]
    daily_message_cap: int = Field(ge=0, le=100)
    daily_calendar_cap: int = Field(ge=0, le=100)
    fixed_restrictions: tuple[str, ...] = FIXED_RESTRICTIONS

    @classmethod
    def from_user(cls, user: User) -> "PreferencesRead":
        return cls(
            autonomy_level=user.default_autonomy,
            category_behaviors={
                key: AutonomyLevel(value) for key, value in (user.autonomy_preferences or {}).items()
            },
            daily_message_cap=user.daily_message_cap,
            daily_calendar_cap=user.daily_calendar_cap,
        )


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    autonomy_level: AutonomyLevel
    category_behaviors: dict[str, AutonomyLevel] = Field(default_factory=dict)
    daily_message_cap: int = Field(ge=0, le=100)
    daily_calendar_cap: int = Field(ge=0, le=100)

    @field_validator("category_behaviors")
    @classmethod
    def validate_categories(cls, value: dict[str, AutonomyLevel]) -> dict[str, AutonomyLevel]:
        unknown = set(value).difference(PREFERENCE_CATEGORIES)
        if unknown:
            raise ValueError(f"Unknown autonomy categories: {', '.join(sorted(unknown))}")
        return value

    def stored_categories(self) -> dict[str, Any]:
        return {key: value.value for key, value in self.category_behaviors.items()}
