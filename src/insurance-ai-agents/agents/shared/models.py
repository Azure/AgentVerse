"""Shared data models for the insurance claims multi-agent system."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
import json


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FraudProbability(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Decision(str, Enum):
    APPROVE = "approve"
    HUMAN_REVIEW = "human_review"
    REJECT = "reject"


class IncidentType(str, Enum):
    COLLISION = "collision"
    THEFT = "theft"
    FIRE = "fire"
    NATURAL_DISASTER = "natural_disaster"
    VANDALISM = "vandalism"
    OTHER = "other"


@dataclass
class ClaimData:
    claim_id: str
    policy_id: str
    customer_id: str
    incident_type: str
    description: str
    estimated_amount: float
    severity: str = ""
    vehicle_info: str = ""
    date_of_incident: str = ""
    location: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass
class IntakeResult:
    claim_id: str
    policy_valid: bool
    extracted_data: dict = field(default_factory=dict)
    severity: str = ""
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskResult:
    claim_id: str
    risk_score: float  # 1-10
    fraud_probability: str  # low/medium/high
    risk_factors: list = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ComplianceResult:
    claim_id: str
    compliant: bool
    decision: str  # approve/human_review/reject
    regulations_checked: list = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FinalDecision:
    claim_id: str
    decision: str  # approve/human_review/reject
    confidence: float
    intake_result: dict = field(default_factory=dict)
    risk_result: dict = field(default_factory=dict)
    compliance_result: dict = field(default_factory=dict)
    reasoning: str = ""
    audit_trail: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
