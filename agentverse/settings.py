"""Configuration for local deterministic triage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class TriageSettings:
    min_ocr_confidence: float = 0.65
    classification_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "financial": 0.78,
            "medical": 0.78,
            "supply": 0.78,
            "unknown": 0.99,
        }
    )
    withdrawal_threshold_eur: float = 5000.0
    reference_date: date = date(2026, 5, 18)


DEFAULT_SETTINGS = TriageSettings()
