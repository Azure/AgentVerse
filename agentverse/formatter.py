"""Result formatting for the playground output."""

from __future__ import annotations

from typing import Any

from agentverse.contracts import TriageResult


def _format_values(values: dict[str, Any]) -> str:
    if not values:
        return ""
    parts = []
    for key, value in values.items():
        parts.append(f"`{key}`={value}")
    return "; ".join(parts)


def format_triage_result(result: TriageResult) -> str:
    context = result.context
    recommendation = result.recommendation
    lines = [
        "# Document triage result",
        "",
        f"- Document ID: `{context.document_id}`",
        f"- Source: `{context.source_uri}`",
        f"- Route: `{context.route}`",
        f"- Classification: `{context.document_type}` / `{context.document_subtype}` ({context.classification_confidence:.2f})",
        f"- Recommendation: `{recommendation.recommended_action}`",
        f"- Status: `{recommendation.decision_status}`",
        f"- Risk: `{recommendation.risk_level}`",
        "",
        "## Reasoning",
        recommendation.reasoning_summary,
    ]

    if context.quality_warnings:
        lines.extend(["", "## Quality warnings"])
        lines.extend(f"- {warning}" for warning in context.quality_warnings)

    if recommendation.evidence:
        lines.extend(["", "## Evidence"])
        for item in recommendation.evidence:
            rendered_values = _format_values(item.values)
            suffix = f" ({rendered_values})" if rendered_values else ""
            lines.append(f"- **{item.source}**: {item.detail}{suffix}")

    if recommendation.missing_information:
        lines.extend(["", "## Missing information"])
        lines.extend(f"- {item}" for item in recommendation.missing_information)

    if recommendation.next_steps:
        lines.extend(["", "## Next steps for human reviewer"])
        lines.extend(f"- {step}" for step in recommendation.next_steps)

    if context.source_citations:
        lines.extend(["", "## Source citations"])
        for citation in context.source_citations[:5]:
            lines.append(f"- Page {citation.page}, {citation.region}: {citation.text}")

    if result.audit_events:
        lines.extend(["", "## Redacted audit trail"])
        for event in result.audit_events:
            lines.append(f"- `{event.event_type}` at {event.timestamp_utc}: {event.summary}")

    return "\n".join(lines)
