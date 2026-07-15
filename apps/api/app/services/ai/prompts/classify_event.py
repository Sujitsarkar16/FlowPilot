"""Prompt builder for life-event classification."""

from app.models.enums import LifeEventType
from app.services.ai.prompts.system import wrap_untrusted

_TYPES = ", ".join(item.value for item in LifeEventType)


def build_classification_prompt(event_type: str, metadata: dict[str, object], content: str) -> str:
    """Return the user message asking for a single classification object."""
    return (
        f"Classify this {event_type} event into exactly one type from: {_TYPES}.\n"
        "Use generic_important_event when unsure. Return JSON with keys: type, "
        "confidence (0-1), importance (low|medium|high), summary, reason.\n"
        f"Trusted metadata: {metadata}\n"
        f"{wrap_untrusted(content)}"
    )
