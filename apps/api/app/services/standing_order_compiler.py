"""Compile natural-language standing orders through the bounded action catalog."""

import logging
from dataclasses import dataclass

from app.schemas.compiled_rule import CompiledRule
from app.services.ai.base import AIProvider
from app.services.ai.prompts.compile_rule import build_compile_rule_prompt
from app.services.ai.prompts.system import SYSTEM_PROMPT
from app.services.ai.schemas import AIError
from app.services.content_safety import sanitize_untrusted_content

logger = logging.getLogger(__name__)


class StandingOrderCompilationError(Exception):
    """Raised when an instruction cannot produce a safe compiled rule."""


@dataclass(frozen=True)
class CompilationResult:
    rule: CompiledRule
    warnings: list[str]


class StandingOrderCompiler:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def compile(self, instruction: str) -> CompilationResult:
        sanitized = sanitize_untrusted_content(instruction)
        try:
            result = await self._provider.generate_structured(
                system=SYSTEM_PROMPT,
                user=build_compile_rule_prompt(sanitized.text),
                schema=CompiledRule,
            )
        except AIError as error:
            logger.warning("standing order compilation failed", extra={"error": str(error), "cause": repr(error.__cause__)})
            raise StandingOrderCompilationError("Could not compile this standing order") from error
        warnings = [*result.data.warnings]
        if sanitized.injection_warnings:
            warnings.append("Instruction-like text was treated as data during compilation.")
        return CompilationResult(
            rule=result.data.model_copy(update={"warnings": warnings}), warnings=warnings
        )
