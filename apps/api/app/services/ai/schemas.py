"""Shared types for the structured AI adapter."""

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from pydantic import BaseModel

StructuredT = TypeVar("StructuredT", bound=BaseModel)


class AIError(Exception):
    """Base failure for the AI adapter."""


class AITimeoutError(AIError):
    """The provider did not respond within the allotted time."""


class AIValidationError(AIError):
    """The model returned output that failed schema validation."""


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True)
class StructuredResult(Generic[StructuredT]):
    data: StructuredT
    usage: TokenUsage = field(default_factory=TokenUsage)
