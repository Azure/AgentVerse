"""Typed I/O contract for {{agent-name}} — building block #1.

Why Pydantic and not a dict? A strict schema is the interface between agents. When agent A
returns a validated ``SampleOutput``, agent B can rely on its shape instead of guessing at
free-form text. Validation also becomes your first output guardrail (block #6): if the model
returns malformed JSON, ``model_validate_json`` raises instead of silently passing garbage
downstream.

Copy this into ``agents/<your-agent>/schemas.py`` and replace the placeholders. Keep the
field names and the JSON block in ``instructions.md`` in sync.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Reusable enum example — constrain the model to a fixed vocabulary."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SampleInput(BaseModel):
    """What the agent receives. Validate untrusted fields here (block #6)."""

    # TODO: replace with your real input fields.
    request: str = Field(..., description="The user request or upstream payload.")


class SampleOutput(BaseModel):
    """What the agent must return. This MUST match the JSON block in instructions.md.

    The next agent (or the backend) validates against this, so treat it as a contract:
    changing it is a breaking change and needs an eval run.
    """

    # TODO: replace with your real output fields.
    field_a: str = Field(..., description="Example string field.")
    field_b: int = Field(..., ge=0, description="Example non-negative integer field.")
    field_c: list[str] = Field(default_factory=list, description="Example list field.")

    # Security surface — populated when the input tries to manipulate the agent.
    security_flag: bool = Field(
        default=False,
        description="True if a manipulation / prompt-injection attempt was detected.",
    )
    severity: Severity = Field(
        default=Severity.LOW,
        description="Raised to HIGH when security_flag is True.",
    )


# Convenience: agents call SampleOutput.model_validate_json(resp.text) to enforce the schema.
