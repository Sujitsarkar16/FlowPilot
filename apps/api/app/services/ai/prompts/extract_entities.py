"""Prompt builder for entity extraction."""

from app.services.ai.prompts.system import wrap_untrusted


def build_entity_prompt(event_type: str, content: str) -> str:
    return (
        f"Extract structured entities from this {event_type} event. Return JSON with an "
        '"entities" array. Each entity has "kind" and a "value" object. Use kinds such '
        "as flight, destination, departure, client, requirement, salary. Normalize dates "
        "to ISO 8601, money as {amount, currency}, and locations by name. Mark identifiers "
        "like PNRs with kind pnr or account_reference. Omit anything not present.\n"
        f"{wrap_untrusted(content)}"
    )
