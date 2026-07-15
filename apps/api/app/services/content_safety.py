"""Sanitize untrusted external content before it reaches the model."""

import re
from dataclasses import dataclass, field

from app.schemas.raw_sources import MAX_CONTENT_CHARS

# Hidden markup and control characters can smuggle instructions past a human reviewer.
_HTML_TAG = re.compile(r"<[^>]+>")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Phrases that look like attempts to override instructions; recorded, never obeyed.
_INJECTION_PATTERNS = (
    re.compile(r"ignore (?:all |the |previous |above )?instructions", re.IGNORECASE),
    re.compile(r"disregard (?:all |the |previous |above )", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"reveal (?:your |the )?(?:prompt|instructions)", re.IGNORECASE),
)


@dataclass(frozen=True)
class SanitizedContent:
    text: str
    truncated: bool = False
    injection_warnings: list[str] = field(default_factory=list)


def sanitize_untrusted_content(
    content: str, *, max_chars: int = MAX_CONTENT_CHARS
) -> SanitizedContent:
    """Strip hidden markup, flag injection attempts, and cap length.

    Warnings are surfaced for audit only. The content is treated as data regardless,
    so a flagged phrase never changes what the model is asked to do.
    """
    warnings = [pattern.pattern for pattern in _INJECTION_PATTERNS if pattern.search(content)]
    cleaned = _HTML_TAG.sub(" ", content)
    cleaned = _CONTROL_CHARS.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    truncated = len(cleaned) > max_chars
    if truncated:
        cleaned = cleaned[:max_chars]
    return SanitizedContent(text=cleaned, truncated=truncated, injection_warnings=warnings)
