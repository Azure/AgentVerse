"""Azure Content Understanding client for uploaded documents and images."""

from __future__ import annotations

import json
import mimetypes
import os
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from azure.identity import AzureCliCredential

from agentverse.contracts import AnalyzerKind, ContentUnderstandingResult, SourceCitation, UploadedDocumentRequest


CONTENT_UNDERSTANDING_API_VERSION = "2025-11-01"
DEFAULT_CONTENT_UNDERSTANDING_ENDPOINT = "https://agent-verse-resource.cognitiveservices.azure.com/"
DOCUMENT_SEARCH_ANALYZER = "prebuilt-documentSearch"
IMAGE_SEARCH_ANALYZER = "prebuilt-imageSearch"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".tiff",
    ".tif",
    ".docx",
    ".xlsx",
    ".pptx",
    ".txt",
    ".html",
    ".htm",
    ".md",
    ".rtf",
    ".eml",
    ".msg",
    ".xml",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".jpe", ".png", ".bmp", ".heif", ".heic"}
SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS
class UnsupportedUploadError(ValueError):
    """Raised when an uploaded file cannot be analyzed by the configured analyzers."""


class ContentUnderstandingClient:
    """Small REST client for Content Understanding prebuilt analyzers."""

    def __init__(
        self,
        endpoint: str | None = None,
        credential: AzureCliCredential | None = None,
        timeout_seconds: int = 180,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self._endpoint = (endpoint or os.environ.get("CONTENT_UNDERSTANDING_ENDPOINT") or DEFAULT_CONTENT_UNDERSTANDING_ENDPOINT).rstrip("/")
        self._credential = credential or AzureCliCredential()
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    def analyze_upload(self, request: UploadedDocumentRequest) -> ContentUnderstandingResult:
        self._validate_upload(request)
        analyzer_id = self._select_analyzer(request.filename, request.content_type, request.analyzer_kind)
        result = self._analyze_binary(analyzer_id, request)

        if analyzer_id == IMAGE_SEARCH_ANALYZER and self._should_fallback_to_document_search(result):
            fallback = self._analyze_binary(DOCUMENT_SEARCH_ANALYZER, request)
            fallback.warnings.append(f"Initial {IMAGE_SEARCH_ANALYZER} result looked document-like or too sparse; reran with {DOCUMENT_SEARCH_ANALYZER}.")
            return fallback

        return result

    def _select_analyzer(self, filename: str, content_type: str, analyzer_kind: AnalyzerKind) -> str:
        extension = Path(filename).suffix.lower()
        if analyzer_kind == AnalyzerKind.DOCUMENT:
            return DOCUMENT_SEARCH_ANALYZER
        if analyzer_kind == AnalyzerKind.IMAGE:
            return IMAGE_SEARCH_ANALYZER
        if extension in IMAGE_EXTENSIONS or content_type.startswith("image/"):
            return IMAGE_SEARCH_ANALYZER
        if extension in DOCUMENT_EXTENSIONS:
            return DOCUMENT_SEARCH_ANALYZER
        raise UnsupportedUploadError(
            f"Unsupported file type '{extension or content_type}'. Supported document/image formats: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )

    def _validate_upload(self, request: UploadedDocumentRequest) -> None:
        if not request.content_bytes:
            raise UnsupportedUploadError("Upload is empty.")
        if len(request.content_bytes) > MAX_UPLOAD_BYTES:
            raise UnsupportedUploadError(f"Upload exceeds the playground limit of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        extension = Path(request.filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedUploadError(
                f"Unsupported file type '{extension or request.content_type}'. Supported document/image formats: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            )

    def _analyze_binary(self, analyzer_id: str, request: UploadedDocumentRequest) -> ContentUnderstandingResult:
        token = self._credential.get_token("https://cognitiveservices.azure.com/.default").token
        operation_url = self._start_analysis(analyzer_id, request, token)
        payload = self._poll_result(operation_url, token)
        return _normalize_result(
            payload=payload,
            analyzer_id=analyzer_id,
            filename=request.filename,
            content_type=request.content_type,
        )

    def _start_analysis(self, analyzer_id: str, request: UploadedDocumentRequest, token: str) -> str:
        url = (
            f"{self._endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyzeBinary"
            f"?api-version={CONTENT_UNDERSTANDING_API_VERSION}"
        )
        http_request = urllib.request.Request(
            url,
            data=request.content_bytes,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": request.content_type or _guess_mime_type(request.filename),
                "x-ms-client-request-id": str(uuid.uuid4()),
            },
        )
        response = self._open_json(http_request, expect_json=False)
        operation_url = response["headers"].get("operation-location")
        if not operation_url:
            raise RuntimeError("Content Understanding did not return an Operation-Location header.")
        return operation_url

    def _poll_result(self, operation_url: str, token: str) -> dict[str, Any]:
        deadline = time.time() + self._timeout_seconds
        while time.time() < deadline:
            http_request = urllib.request.Request(operation_url, method="GET", headers={"Authorization": f"Bearer {token}"})
            payload = self._open_json(http_request)["payload"]
            status = str(payload.get("status", "")).lower()
            if status == "succeeded":
                return payload
            if status == "failed":
                raise RuntimeError(f"Content Understanding analysis failed: {payload.get('error', payload)}")
            time.sleep(self._poll_interval_seconds)
        raise TimeoutError("Content Understanding analysis timed out.")

    @staticmethod
    def _open_json(request: urllib.request.Request, expect_json: bool = True) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8") if expect_json else ""
                return {
                    "headers": {key.lower(): value for key, value in response.headers.items()},
                    "payload": json.loads(body) if body else {},
                }
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Content Understanding request failed with HTTP {exc.code}: {body}") from exc

    @staticmethod
    def _should_fallback_to_document_search(result: ContentUnderstandingResult) -> bool:
        text = f"{result.markdown}\n{result.summary}".lower()
        return len(text.strip()) < 80


def build_upload_request_from_path(
    file_path: str,
    metadata: dict[str, str] | None = None,
    analyzer_kind: AnalyzerKind = AnalyzerKind.AUTO,
) -> UploadedDocumentRequest:
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Upload file does not exist: {file_path}")
    content_type = _guess_mime_type(path.name)
    return UploadedDocumentRequest(
        filename=path.name,
        content_type=content_type,
        content_bytes=path.read_bytes(),
        analyzer_kind=analyzer_kind,
        metadata=metadata or {},
    )


def _normalize_result(payload: dict[str, Any], analyzer_id: str, filename: str, content_type: str) -> ContentUnderstandingResult:
    result = payload.get("result", {})
    contents = result.get("contents") or []
    first_content = contents[0] if contents else {}
    markdown = str(first_content.get("markdown") or "")
    summary = _extract_summary(first_content, markdown)
    warnings = [_format_warning(warning) for warning in result.get("warnings", [])]
    warnings.extend(_format_warning(warning) for warning in first_content.get("warnings", []) if isinstance(warning, dict))
    return ContentUnderstandingResult(
        document_id=str(payload.get("id") or uuid.uuid4()),
        filename=filename,
        content_type=str(first_content.get("mimeType") or content_type or _guess_mime_type(filename)),
        analyzer_id=str(first_content.get("analyzerId") or result.get("analyzerId") or analyzer_id),
        api_version=str(result.get("apiVersion") or CONTENT_UNDERSTANDING_API_VERSION),
        markdown=markdown,
        summary=summary,
        fields=first_content.get("fields") or {},
        tables=first_content.get("tables") or [],
        pages=first_content.get("pages") or [],
        warnings=warnings,
        source_citations=_build_citations(first_content, markdown),
        raw_result=result,
    )


def _extract_summary(content: dict[str, Any], markdown: str) -> str:
    fields = content.get("fields") or {}
    for key in ("Summary", "summary", "Description", "description"):
        field = fields.get(key)
        if isinstance(field, dict):
            value = field.get("valueString") or field.get("value")
            if value:
                return str(value)
        if isinstance(field, str):
            return field
    return markdown[:600]


def _build_citations(content: dict[str, Any], markdown: str) -> list[SourceCitation]:
    pages = content.get("pages") or []
    if pages:
        citations = []
        for page in pages[:3]:
            page_number = int(page.get("pageNumber") or page.get("page_number") or 1)
            lines = page.get("lines") or []
            text = " ".join(str(line.get("content", "")) for line in lines[:3] if isinstance(line, dict)).strip()
            citations.append(SourceCitation(page=page_number, region="content_understanding_page", text=text or markdown[:180]))
        return citations
    if markdown:
        return [SourceCitation(page=1, region="content_understanding_markdown", text=markdown[:180])]
    return []


def _format_warning(warning: dict[str, Any]) -> str:
    code = warning.get("code", "warning")
    message = warning.get("message", "")
    return f"{code}: {message}" if message else str(code)


def _guess_mime_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"
