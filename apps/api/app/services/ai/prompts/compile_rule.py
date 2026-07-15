"""Prompt builder for compiling a standing order into the action catalog."""

from app.schemas.compiled_rule import ACTION_CATALOG, MAX_ACTION_TEMPLATES
from app.services.ai.prompts.system import wrap_untrusted


def build_compile_rule_prompt(instruction: str) -> str:
    """Ask for a bounded, schema-validated rule; the instruction remains inert data."""
    catalog = ", ".join(sorted(ACTION_CATALOG))
    return (
        "Compile the user's standing order into the supplied JSON schema. Select only action "
        f"types from: {catalog}. Include at most {MAX_ACTION_TEMPLATES} actions. Never grant "
        "automatic execution to a red-risk action. Explain the rule briefly and list any caveats.\n"
        f"{wrap_untrusted(instruction)}"
    )
