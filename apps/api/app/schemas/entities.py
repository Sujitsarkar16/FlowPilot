"""Structured entity-extraction contract with deterministic post-validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Entity kinds whose values reference sensitive identifiers and must be masked.
SENSITIVE_KINDS = frozenset({"pnr", "account_reference", "booking_reference", "passport"})


class ExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: str = Field(min_length=1, max_length=80)
    value: dict[str, object]

    @property
    def is_sensitive(self) -> bool:
        return self.kind.lower() in SENSITIVE_KINDS


class ExtractedEntities(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entities: list[ExtractedEntity] = Field(default_factory=list, max_length=50)

    @field_validator("entities")
    @classmethod
    def drop_invalid_dates(cls, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """Reject entities carrying an unparseable ``date``/``datetime`` value."""
        valid: list[ExtractedEntity] = []
        for entity in entities:
            candidate = entity.value.get("date") or entity.value.get("datetime")
            if isinstance(candidate, str):
                try:
                    datetime.fromisoformat(candidate.replace("Z", "+00:00"))
                except ValueError:
                    continue
            valid.append(entity)
        return valid
