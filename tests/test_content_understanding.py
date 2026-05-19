from __future__ import annotations

from agentverse.content_understanding import (
    DOCUMENT_SEARCH_ANALYZER,
    IMAGE_SEARCH_ANALYZER,
    ContentUnderstandingClient,
    UnsupportedUploadError,
)
from agentverse.contracts import AnalyzerKind, ContentUnderstandingResult, UploadedDocumentRequest


def test_content_understanding_selects_document_search_for_documents() -> None:
    client = ContentUnderstandingClient()

    assert client._select_analyzer("credit_application.pdf", "application/pdf", AnalyzerKind.AUTO) == DOCUMENT_SEARCH_ANALYZER


def test_content_understanding_selects_image_search_for_images() -> None:
    client = ContentUnderstandingClient()

    assert client._select_analyzer("clinical_note.png", "image/png", AnalyzerKind.AUTO) == IMAGE_SEARCH_ANALYZER


def test_document_like_image_keeps_image_search_when_summary_is_useful() -> None:
    class FakeClient(ContentUnderstandingClient):
        def _analyze_binary(self, analyzer_id: str, request: UploadedDocumentRequest) -> ContentUnderstandingResult:
            return ContentUnderstandingResult(
                document_id="fake",
                filename=request.filename,
                content_type=request.content_type,
                analyzer_id=analyzer_id,
                api_version="test",
                markdown="short image markdown",
                summary="The image shows a clinical note for patient PAT-3001 reporting chest pressure and shortness of breath.",
            )

    result = FakeClient().analyze_upload(
        UploadedDocumentRequest(filename="clinical_note.png", content_type="image/png", content_bytes=b"fake")
    )

    assert result.analyzer_id == IMAGE_SEARCH_ANALYZER


def test_content_understanding_rejects_unsupported_upload_type() -> None:
    client = ContentUnderstandingClient()
    request = UploadedDocumentRequest(filename="sample.exe", content_type="application/octet-stream", content_bytes=b"abc")

    try:
        client.analyze_upload(request)
    except UnsupportedUploadError as exc:
        assert "Unsupported file type" in str(exc)
    else:
        raise AssertionError("Expected unsupported upload to be rejected before any Azure call.")
