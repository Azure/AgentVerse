"""Foundry-backed triage service for uploaded documents and images."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.core.credentials import TokenCredential
from json_repair import repair_json

from agentverse.audit import AuditLogger
from agentverse.content_understanding import ContentUnderstandingClient, build_upload_request_from_path
from agentverse.contracts import (
    AgentRecommendation,
    ContentUnderstandingResult,
    DocumentContext,
    DocumentTriageRequest,
    DocumentType,
    OcrTable,
    TriageResult,
    UploadedDocumentRequest,
)
from agentverse.credentials import default_agentverse_credential
from agentverse.foundry_definitions import AGENT_NAMES, MODEL_DEPLOYMENT_NAME, PROJECT_ENDPOINT
from agentverse.history_snapshots import HistorySnapshotBuilder


class FoundryTriageService:
    """Analyze uploads with Content Understanding and route through Foundry prompt agents."""

    def __init__(
        self,
        project_endpoint: str | None = None,
        model_deployment_name: str | None = None,
        content_client: ContentUnderstandingClient | None = None,
        credential: TokenCredential | None = None,
    ) -> None:
        self._project_endpoint = project_endpoint or os.environ.get("AZURE_AI_PROJECT_ENDPOINT", PROJECT_ENDPOINT)
        self._model = model_deployment_name or os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", MODEL_DEPLOYMENT_NAME)
        self._credential = credential or _default_credential()
        self._client = AIProjectClient(endpoint=self._project_endpoint, credential=self._credential)
        self._openai_client = self._client.get_openai_client()
        self._content_client = content_client or ContentUnderstandingClient(credential=self._credential)
        self._snapshots = HistorySnapshotBuilder()

    def run(self, request: DocumentTriageRequest) -> TriageResult:
        return self.recommend(self.intake(request))

    def intake(self, request: DocumentTriageRequest) -> DocumentContext:
        upload = build_upload_request_from_path(
            request.file_path,
            metadata=request.metadata,
            analyzer_kind=request.analyzer_kind,
        )
        return self.intake_upload(upload)

    def run_upload(self, request: UploadedDocumentRequest) -> TriageResult:
        return self.recommend(self.intake_upload(request))

    def intake_upload(self, request: UploadedDocumentRequest) -> DocumentContext:
        audit = AuditLogger()
        content = self._content_client.analyze_upload(request)
        analyzer_context = _build_analyzer_context(content)
        intake_payload = {
            "source": "azure_content_understanding",
            "file": {
                "document_id": content.document_id,
                "filename": content.filename,
                "content_type": content.content_type,
                "requested_analyzer_kind": str(request.analyzer_kind),
            },
            "content_understanding_summary": analyzer_context,
            "content_understanding_evidence": {
                "markdown_excerpt": content.markdown[:4000],
                "fields": content.fields,
                "tables": content.tables[:5],
                "pages": _compact_pages(content.pages),
                "source_citations": [citation.model_dump() for citation in content.source_citations],
            },
        }
        intake_response = self._invoke_json(AGENT_NAMES["intake"], intake_payload)
        fields = _normalize_fields(intake_response.get("extracted_fields", {}))
        fields.update(request.metadata)
        fields.update(
            {
                "source_filename": content.filename,
                "content_type": content.content_type,
                "content_understanding_analyzer": content.analyzer_id,
                "content_understanding_summary": analyzer_context.get("summary", ""),
            }
        )
        document_type = _document_type_from_response(intake_response)
        route = str(intake_response.get("route", "manual_review"))
        context = DocumentContext(
            document_id=f"upload-{content.document_id}",
            source_uri=f"upload://{content.filename}",
            document_type=document_type,
            document_subtype=str(intake_response.get("document_subtype", "unknown")),
            route=route if route in {"financial", "medical", "supply", "manual_review"} else "manual_review",
            language="unknown",
            extracted_text=content.summary or content.markdown,
            fields=fields,
            analyzer_context=analyzer_context,
            tables=[OcrTable(name=f"table_{index + 1}", rows=_table_rows(table)) for index, table in enumerate(content.tables[:5])],
            entities={},
            classification_confidence=float(intake_response.get("classification_confidence", 0.0) or 0.0),
            quality_warnings=list(intake_response.get("quality_warnings", content.warnings)),
            source_citations=content.source_citations,
            audit_events=[],
        )
        audit.record(
            "content_understanding_intake_completed",
            "Content Understanding analyzed the upload and Foundry intake selected the route.",
            {
                "agent": AGENT_NAMES["intake"],
                "analyzer": content.analyzer_id,
                "route": context.route,
                "document_type": context.document_type,
                "filename": content.filename,
            },
        )
        return context.model_copy(update={"audit_events": audit.events})

    def recommend(self, context: DocumentContext) -> TriageResult:
        audit = AuditLogger(context.audit_events)
        snapshot = self._snapshots.build(context)
        specialist_agent = AGENT_NAMES.get(context.route, AGENT_NAMES["manual_review"])
        recommendation_payload = {
            "document_context": context.model_dump(mode="json"),
            "analyzer_context": context.analyzer_context,
            "history_snapshot": snapshot,
            "safety_instruction": "Return recommendation JSON only. The human reviewer executes any final action.",
        }
        recommendation_json = self._invoke_json(specialist_agent, recommendation_payload)
        recommendation_json = _normalize_recommendation_json(recommendation_json)
        recommendation = AgentRecommendation.model_validate(recommendation_json)
        audit.record(
            "foundry_specialist_completed",
            "Foundry specialist prompt agent produced the recommendation.",
            {"agent": specialist_agent, "recommended_action": recommendation.recommended_action},
        )
        events = audit.events
        context = context.model_copy(update={"audit_events": events})
        return TriageResult(context=context, recommendation=recommendation, audit_events=events, review_required=True)

    def _invoke_json(self, agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._openai_client.responses.create(
            model=self._model,
            input=json.dumps(payload, ensure_ascii=False),
            extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
        )
        text = response.output[0].content[0].text
        try:
            return _extract_json(text)
        except json.JSONDecodeError as exc:
            return self._repair_json_response(agent_name, text, exc)

    def _repair_json_response(self, agent_name: str, text: str, parse_error: json.JSONDecodeError) -> dict[str, Any]:
        repair_payload = {
            "task": "Convert the malformed agent response into one valid JSON object.",
            "agent_name": agent_name,
            "parse_error": str(parse_error),
            "rules": [
                "Return only valid JSON.",
                "Do not add new facts.",
                "Preserve the same keys, lists, strings, numbers, and booleans when possible.",
                "Escape any quotes inside string values.",
                "Remove markdown fences or explanatory text.",
            ],
            "malformed_response": text,
        }
        response = self._openai_client.responses.create(
            model=self._model,
            input=json.dumps(repair_payload, ensure_ascii=False),
            temperature=0,
            text={"format": {"type": "json_object"}},
        )
        repaired_text = response.output[0].content[0].text
        return _extract_json(repaired_text)


def _document_type_from_response(intake_response: dict[str, Any]) -> DocumentType:
    value = str(intake_response.get("document_type", "unknown"))
    try:
        return DocumentType(value)
    except ValueError:
        return DocumentType.UNKNOWN


def _normalize_fields(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_recommendation_json(value: dict[str, Any]) -> dict[str, Any]:
    evidence = value.get("evidence")
    if isinstance(evidence, list):
        normalized_evidence = []
        for item in evidence:
            if not isinstance(item, dict):
                normalized_evidence.append({"source": "agent_response", "detail": str(item), "values": {}})
                continue
            values = item.get("values")
            if values is None:
                item["values"] = {}
            elif not isinstance(values, dict):
                item["values"] = {"items": values}
            normalized_evidence.append(item)
        value["evidence"] = normalized_evidence
    return value


def _compact_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted = []
    for page in pages[:5]:
        lines = page.get("lines") or []
        compacted.append(
            {
                "pageNumber": page.get("pageNumber") or page.get("page_number"),
                "text": " ".join(str(line.get("content", "")) for line in lines[:8] if isinstance(line, dict)),
            }
        )
    return compacted


def _build_analyzer_context(content: ContentUnderstandingResult) -> dict[str, Any]:
    page_text = []
    for page in content.pages[:3]:
        lines = page.get("lines") or []
        rendered = " ".join(str(line.get("content", "")) for line in lines[:12] if isinstance(line, dict)).strip()
        if rendered:
            page_text.append(
                {
                    "page": page.get("pageNumber") or page.get("page_number") or 1,
                    "text": rendered[:1000],
                }
            )
    return {
        "analyzer_id": content.analyzer_id,
        "api_version": content.api_version,
        "summary": content.summary or content.markdown[:1000],
        "warnings": content.warnings,
        "field_keys": sorted(str(key) for key in content.fields.keys()),
        "table_count": len(content.tables),
        "page_excerpts": page_text,
        "markdown_excerpt": content.markdown[:1600],
    }


def _table_rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    rows = table.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    cells = table.get("cells")
    if not isinstance(cells, list):
        return []
    rendered_rows: dict[int, dict[str, Any]] = {}
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        row_index = int(cell.get("rowIndex", 0))
        column_index = str(cell.get("columnIndex", 0))
        rendered_rows.setdefault(row_index, {})[column_index] = cell.get("content", "")
    return [rendered_rows[index] for index in sorted(rendered_rows)]


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    candidates = [stripped]
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        candidates.append(match.group(0))

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            repaired = repair_json(candidate, return_objects=True)
            if isinstance(repaired, dict):
                return repaired
            continue
        if isinstance(parsed, dict):
            return parsed

    if last_error:
        raise last_error
    raise ValueError("Agent response did not contain a JSON object.")


def _default_credential() -> TokenCredential:
    return default_agentverse_credential()
