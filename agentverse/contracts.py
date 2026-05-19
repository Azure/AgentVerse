"""Shared contracts for the document triage workflow."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    FINANCIAL = "financial"
    MEDICAL = "medical"
    SUPPLY = "supply"
    UNKNOWN = "unknown"


class DecisionStatus(str, Enum):
    READY_FOR_REVIEW = "ready_for_review"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    BLOCKED_MISSING_DATA = "blocked_missing_data"
    UNSUPPORTED_DOCUMENT = "unsupported_document"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    NOT_APPLICABLE = "not_applicable"


class RecommendedAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    HOLD = "hold"
    ESCALATE = "escalate"
    SUMMARIZE = "summarize"
    PRESCRIBE_FOR_REVIEW = "prescribe_for_review"
    BUY = "buy"
    SHIP_IMMEDIATELY = "ship_immediately"
    STORE_IN_INVENTORY = "store_in_inventory"
    CONSOLIDATE_SHIPMENT = "consolidate_shipment"
    RELEASE_RESERVED_STOCK = "release_reserved_stock"
    DISPUTE_SUPPLIER_DOCUMENT = "dispute_supplier_document"
    ACCEPT_DELIVERY = "accept_delivery"
    PARTIALLY_ACCEPT_DELIVERY = "partially_accept_delivery"
    REQUEST_PARTIAL_FULFILLMENT = "request_partial_fulfillment"
    UNKNOWN = "unknown"


Route = Literal["financial", "medical", "supply", "manual_review", "unknown"]


class AnalyzerKind(str, Enum):
    AUTO = "auto"
    DOCUMENT = "document"
    IMAGE = "image"


class DocumentTriageRequest(BaseModel):
    """Input submitted from DevUI for a local file path."""

    file_path: str = Field(
        description="Local path to a supported document or image file.",
    )
    analyzer_kind: AnalyzerKind = Field(
        default=AnalyzerKind.AUTO,
        description="Analyzer selection hint. Auto lets the service choose Content Understanding analyzers.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional reviewer/user/customer metadata supplied with the document.",
    )


class UploadedDocumentRequest(BaseModel):
    """Binary upload submitted by the reviewer dashboard."""

    filename: str
    content_type: str = "application/octet-stream"
    content_bytes: bytes = Field(repr=False)
    analyzer_kind: AnalyzerKind = AnalyzerKind.AUTO
    metadata: dict[str, str] = Field(default_factory=dict)


class SourceCitation(BaseModel):
    page: int = Field(default=1)
    region: str
    text: str


class OcrTable(BaseModel):
    name: str
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ContentUnderstandingResult(BaseModel):
    """Normalized Azure Content Understanding result for an uploaded file."""

    document_id: str
    filename: str
    content_type: str
    analyzer_id: str
    api_version: str
    markdown: str = ""
    summary: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    pages: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    raw_result: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    event_type: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp_utc: str


class DocumentContext(BaseModel):
    """Normalized handoff envelope from intake to a specialized agent."""

    model_config = ConfigDict(use_enum_values=True)

    document_id: str
    source_uri: str
    document_type: DocumentType
    document_subtype: str
    route: Route
    language: str
    extracted_text: str
    fields: dict[str, Any] = Field(default_factory=dict)
    analyzer_context: dict[str, Any] = Field(default_factory=dict)
    tables: list[OcrTable] = Field(default_factory=list)
    entities: dict[str, list[str]] = Field(default_factory=dict)
    classification_confidence: float
    quality_warnings: list[str] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    source: str
    detail: str
    values: dict[str, Any] = Field(default_factory=dict)


class AgentRecommendation(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    recommended_action: RecommendedAction
    decision_status: DecisionStatus
    risk_level: RiskLevel
    reasoning_summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class TriageResult(BaseModel):
    context: DocumentContext
    recommendation: AgentRecommendation
    audit_events: list[AuditEvent] = Field(default_factory=list)
    review_required: bool = True
