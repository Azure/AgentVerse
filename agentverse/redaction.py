"""PII/PHI-aware redaction for audit records."""

from __future__ import annotations

import re
from typing import Any


ID_PATTERNS = [
    re.compile(r"\bCUST-\d+\b", re.IGNORECASE),
    re.compile(r"\bACCT-\d+\b", re.IGNORECASE),
    re.compile(r"\bPAT-\d+\b", re.IGNORECASE),
    re.compile(r"\bPO-\d+\b", re.IGNORECASE),
]

SENSITIVE_KEYS = {
    "account",
    "account_id",
    "account_holder",
    "applicant_name",
    "customer_id",
    "email",
    "name",
    "patient_id",
    "patient_name",
}


def redact_text(value: str) -> str:
    redacted = value
    for pattern in ID_PATTERNS:
        redacted = pattern.sub("[REDACTED_ID]", redacted)
    return redacted


def redact_value(key: str, value: Any) -> Any:
    normalized_key = key.lower()
    if normalized_key in SENSITIVE_KEYS or normalized_key.endswith("_id"):
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return redact_dict(value)
    if isinstance(value, list):
        return [redact_value(normalized_key, item) for item in value]
    return value


def redact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: redact_value(key, value) for key, value in values.items()}
