"""In-memory audit trail for a single workflow run."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agentverse.contracts import AuditEvent
from agentverse.redaction import redact_dict


class AuditLogger:
    """Collect redacted audit events that can be returned with the result."""

    def __init__(self, initial_events: list[AuditEvent] | None = None) -> None:
        self._events = list(initial_events or [])

    @property
    def events(self) -> list[AuditEvent]:
        return list(self._events)

    def record(self, event_type: str, summary: str, details: dict[str, Any] | None = None) -> None:
        self._events.append(
            AuditEvent(
                event_type=event_type,
                summary=summary,
                details=redact_dict(details or {}),
                timestamp_utc=datetime.now(UTC).isoformat(),
            )
        )
