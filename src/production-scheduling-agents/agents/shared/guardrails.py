"""Guardrails for untrusted input.

Free-text fields arriving from MES/ERP (operator comments, order notes) are
untrusted: they may carry prompt-injection attempts. The check runs BEFORE any
text reaches an agent prompt — a flagged disruption short-circuits to `reject`
without ever being shown to the LLM.
"""

from __future__ import annotations

import re

# Deliberately simple, high-precision patterns: manipulation attempts against a
# scheduling agent, not a general content filter.
_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"\bsystem\s+override\b", "claims a system override"),
    (r"\bignore\s+(all|any|previous|prior|the)\b", "asks to ignore instructions or constraints"),
    (r"\bdisregard\b.{0,40}\b(constraint|instruction|safety|rule)", "asks to disregard constraints"),
    (r"\bnew\s+instructions?\b", "injects replacement instructions"),
    (r"\b(disable|bypass|turn\s+off)\b.{0,40}\b(safety|interlock|constraint|guardrail)", "asks to disable safety mechanisms"),
    (r"\b(1[2-9]\d|[2-9]\d\d)\s*%\s*(of\s+)?capacity\b", "demands above-100% capacity"),
    (r"\byou\s+are\s+now\b", "attempts role reassignment"),
]


def detect_prompt_injection(text: str | None) -> tuple[bool, str]:
    """Return (flagged, reason). Empty/None text is never flagged."""
    if not text:
        return False, ""
    lowered = text.lower()
    for pattern, reason in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return True, reason
    return False, ""
