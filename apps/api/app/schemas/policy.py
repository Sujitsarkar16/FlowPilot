"""Typed policy outcomes for candidate actions before persistence."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import ActionStatus


class PolicyReason(StrEnum):
    """Stable, machine-readable reasons for policy outcomes."""

    CONNECTION_MISSING = "connection_missing"
    SCOPES_MISSING = "scopes_missing"
    TEMPLATE_BLOCKED = "template_blocked"
    RED_REQUIRES_APPROVAL = "red_requires_approval"
    ACTION_REQUIRES_APPROVAL = "action_requires_approval"
    SAFE_AUTOMATIC = "safe_automatic"
    TRUSTED_AUTOMATIC = "trusted_automatic"
    SUGGEST_MANUAL = "suggest_manual"
    OBSERVE_MANUAL = "observe_manual"



class PolicyDecision(BaseModel):
    """Action persistence fields selected by policy evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ActionStatus
    requires_approval: bool
    reason: PolicyReason

    @model_validator(mode="after")
    def validate_approval_status(self) -> "PolicyDecision":
        if self.status is ActionStatus.WAITING_APPROVAL and not self.requires_approval:
            raise ValueError("waiting approval actions must require approval")
        return self

    def action_fields(self) -> dict[str, ActionStatus | bool]:
        """Return exactly the fields consumed by ``Action`` persistence."""
        return {"status": self.status, "requires_approval": self.requires_approval}


ActionPolicyDecision = PolicyDecision
