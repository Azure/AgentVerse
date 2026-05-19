from __future__ import annotations

from fastapi.testclient import TestClient

from agentverse.contracts import (
    AgentRecommendation,
    DecisionStatus,
    DocumentContext,
    DocumentType,
    EvidenceItem,
    RecommendedAction,
    RiskLevel,
    TriageResult,
    UploadedDocumentRequest,
)
from agentverse.review_dashboard import build_review_view_model, create_review_dashboard_app, render_review_page


class FakeUploadService:
    def __init__(self, result: TriageResult) -> None:
        self.result = result
        self.last_request: UploadedDocumentRequest | None = None

    def run_upload(self, request: UploadedDocumentRequest) -> TriageResult:
        self.last_request = request
        return self.result


def make_result() -> TriageResult:
    context = DocumentContext(
        document_id="upload-test",
        source_uri="upload://withdrawal_order_high_risk.png",
        document_type=DocumentType.FINANCIAL,
        document_subtype="withdrawal_order",
        route="financial",
        language="unknown",
        extracted_text="Cash withdrawal order for account ACCT-2002 requesting 10000 EUR.",
        fields={
            "source_filename": "withdrawal_order_high_risk.png",
            "content_understanding_analyzer": "prebuilt-documentSearch",
            "account_id": "ACCT-2002",
            "requested_amount_eur": 10000,
            "location": "Valencia Centro Branch",
            "requested_datetime": "2026-05-18T22:45:00",
        },
        classification_confidence=0.92,
        quality_warnings=[],
    )
    recommendation = AgentRecommendation(
        recommended_action=RecommendedAction.HOLD,
        decision_status=DecisionStatus.NEEDS_HUMAN_REVIEW,
        risk_level=RiskLevel.HIGH,
        reasoning_summary="The intake and financial agents found a suspicious high-value withdrawal.",
        evidence=[
            EvidenceItem(
                source="content_understanding",
                detail="The uploaded document contains a high-value withdrawal order.",
                values={"requested_amount_eur": 10000},
            )
        ],
        next_steps=["Verify identity before releasing funds."],
    )
    return TriageResult(context=context, recommendation=recommendation, audit_events=[], review_required=True)


def test_review_page_uses_upload_form_without_case_selector() -> None:
    html = render_review_page()

    assert 'data-testid="file-input"' in html
    assert 'data-testid="fixture-select"' not in html
    assert 'data-testid="role-select"' not in html
    assert "The intake agent decides" in html


def test_review_view_model_uses_content_understanding_details() -> None:
    model = build_review_view_model(make_result())

    assert model["strategy"] == "Hold and escalate before releasing funds"
    assert model["route"] == "Financial"
    assert any(detail["label"] == "Analyzer" and detail["value"] == "prebuilt-documentSearch" for detail in model["case_details"])


def test_medical_case_details_fall_back_to_clinical_complaint() -> None:
    result = make_result()
    context = result.context.model_copy(
        update={
            "document_type": DocumentType.MEDICAL,
            "document_subtype": "clinical_note",
            "route": "medical",
            "fields": {
                "source_filename": "clinical_note_red_flags.png",
                "content_understanding_analyzer": "prebuilt-imageSearch",
                "patient_id": "PAT-3001",
                "chief_complaint": "chest pressure with shortness of breath and left arm pain",
                "vitals": {"blood_pressure": "168/102"},
            },
        }
    )

    model = build_review_view_model(result.model_copy(update={"context": context}))

    assert any(
        detail["label"] == "Symptoms" and "chest pressure" in detail["value"]
        for detail in model["case_details"]
    )


def test_review_dashboard_upload_endpoint_renders_summary() -> None:
    result = make_result()
    service = FakeUploadService(result)
    client = TestClient(create_review_dashboard_app(service=service))
    response = client.post(
        "/analyze",
        files={"file": ("withdrawal_order_high_risk.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    assert service.last_request is not None
    assert service.last_request.filename == "withdrawal_order_high_risk.png"
    assert service.last_request.metadata == {}
    assert "Hold and escalate before releasing funds" in response.text
    assert "<built-in method values" not in response.text


def test_review_page_highlights_strategy_before_trace_details() -> None:
    html = render_review_page(result=make_result())

    assert 'data-testid="recommended-action"' in html
    assert 'data-testid="trace-json"' in html
    assert html.index('data-testid="recommended-action"') < html.index('data-testid="trace-json"')
