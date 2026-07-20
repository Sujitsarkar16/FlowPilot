"""Prompt builder for compiling a standing order into the action catalog."""

from app.models.enums import LifeEventType
from app.schemas.compiled_rule import ACTION_CATALOG, MAX_ACTION_TEMPLATES
from app.services.ai.prompts.system import wrap_untrusted

_TRIGGER_TYPES = ", ".join(item.value for item in LifeEventType)


def build_compile_rule_prompt(instruction: str) -> str:
    """Ask for a bounded, schema-validated rule; the instruction remains inert data."""
    catalog = "\n".join(
        f"- {action_type}: connector={connector}; risk_level={risk.value}; "
        f"approval_mode={approval_mode}"
        for action_type, (connector, risk, approval_mode) in sorted(ACTION_CATALOG.items())
    )
    return (
        "Compile the user's standing order into a JSON object with exactly these top-level keys:\n"
        '- "schema_version": the string "1.0".\n'
        f'- "trigger_event_types": array of one or more of: {_TRIGGER_TYPES}.\n'
        '- "entity_conditions": array (use [] when none). Each item has "field", '
        '"operator" (equals|contains|exists), and optional "value".\n'
        '- "action_templates": array of the actions to run. Each item has exactly '
        '"action_type", "connector", "risk_level", "approval_mode", and optional "input" '
        "(an object).\n"
        '- "explanation": a brief sentence describing the rule.\n'
        '- "warnings": array of caveat strings (use [] when none).\n\n'
        "Use only the action types below, with the exact connector, risk_level, and approval_mode "
        f"shown. Include at most {MAX_ACTION_TEMPLATES} unique actions and never repeat an "
        "action_type. Never grant automatic execution to a red-risk action.\n\n"
        f"Action catalog:\n{catalog}\n\n"
        "For a flight/travel confirmation, trigger on travel_booked and use the travel.* actions "
        "the user asked for. For a confirmed client project, trigger on client_confirmed and use "
        "client.create_folder for the project folder; client.generate_documents once for "
        "requirements, proposal, and invoice documents; client.create_repository for the private "
        "GitHub repository; client.create_calendar_event for kickoff suggestions; and "
        "client.notify_client for the reply, with approval_required. For subscription renewal "
        "or active-subscription checks, trigger on subscription_renewal and use "
        "subscription.check_renewal.\n"
        f"{wrap_untrusted(instruction)}"
    )
