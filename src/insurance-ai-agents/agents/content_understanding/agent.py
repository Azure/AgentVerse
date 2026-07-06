"""Azure AI Content Understanding integration.

Why this exists
---------------
Until now the claims-intake agent did vision-OCR on the customer's attachment
(PDF claim report, photo of damage) by sending the bytes straight to a
chat-completion call with GPT-vision. That works but:

  * it is expensive (vision tokens are billed at a premium)
  * it has no schema guarantee — the LLM may hallucinate field names
  * it cannot reliably handle multi-page PDFs or audio

Azure AI Content Understanding (GA Nov 2024) solves all three: one REST
endpoint, schema-driven extraction, native PDF / image / audio / video, and a
flat per-page price. It is the Microsoft answer for "extract structured data
from unstructured documents" and is the right primary tool here.

Design
------
* A single custom analyzer ``accident-report-en`` is created the first time
  ``ensure_analyzer()`` is called (idempotent — checks existence first).
* ``extract_from_bytes(blob, mime_type)`` and ``extract_from_text(text)``
  return a dict with the schema below. They poll the long-running operation
  until the result is ready (CU is async — submit returns 202 + operation
  URL).
* Auth uses ``DefaultAzureCredential`` against the
  ``https://cognitiveservices.azure.com`` audience so the same MI / az-cli /
  workload identity story as the rest of the stack applies.

This module never raises if the endpoint is not configured: callers should
treat ``ensure_analyzer()`` returning ``False`` as "CU is disabled, fall back
to LLM-only intake".
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any

import httpx
from azure.identity.aio import DefaultAzureCredential

from agents.shared.brand import BRAND_NAME

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------
# Mirrors the fields the downstream Intake agent expects to see. Field types
# follow the Content Understanding schema spec
# (https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/schema)
# so the service can decide between extraction (transcribe) and generation
# (infer/classify) per field.
ACCIDENT_REPORT_SCHEMA: dict[str, Any] = {
    "name": "AccidentReport",
    "description": (
        "Structured data extracted from a car claim report "
        f"submitted by a customer of {BRAND_NAME}. Supports PDFs "
        "(unified European format), damage photos and audio notes."
    ),
    "fields": {
        "incident_date": {
            "type": "date",
            "method": "extract",
            "description": "Date on which the claim occurred (dd/mm/yyyy)",
        },
        "incident_time": {
            "type": "time",
            "method": "extract",
            "description": "Approximate time of the claim in 24h format",
        },
        "incident_location": {
            "type": "string",
            "method": "extract",
            "description": "Incident location (address, city, province)",
        },
        "incident_type": {
            "type": "string",
            "method": "classify",
            "description": "Detected incident type",
            "enum": [
                "collision",
                "theft",
                "fire",
                "vandalism",
                "weather",
                "glass_breakage",
                "other",
            ],
        },
        "insured_vehicle_plate": {
            "type": "string",
            "method": "extract",
            "description": "License plate of the insured vehicle",
        },
        "third_party_vehicle_plate": {
            "type": "string",
            "method": "extract",
            "description": "License plate of the third-party vehicle involved, if applicable",
        },
        "damage_description": {
            "type": "string",
            "method": "generate",
            "description": (
                "One-sentence summary of the visible damages, written in "
                "formal English suitable for a report."
            ),
        },
        "damage_severity": {
            "type": "string",
            "method": "classify",
            "description": "Severity of the observed damages",
            "enum": ["minor", "moderate", "severe", "total_loss"],
        },
        "estimated_amount_eur": {
            "type": "number",
            "method": "generate",
            "description": (
                "Estimated repair amount in euros. If the input does not "
                "indicate it, leave 0."
            ),
        },
        "police_report_filed": {
            "type": "string",
            "method": "classify",
            "description": "Whether a police report has been filed",
            "enum": ["yes", "no", "unknown"],
        },
        "injuries_reported": {
            "type": "string",
            "method": "classify",
            "description": "Whether any injuries are reported",
            "enum": ["yes", "no", "unknown"],
        },
        "summary": {
            "type": "string",
            "method": "generate",
            "description": (
                "One-sentence executive summary of the claim, useful for "
                "the human operator to read at a glance."
            ),
        },
    },
}

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------
ANALYZER_ID = "accident-report-en"
API_VERSION = "2025-05-01-preview"
BASE_ANALYZER_ID = "prebuilt-documentAnalyzer"  # Pro multimodal sibling: "prebuilt-multimodalAnalyzerPro"

_credential: DefaultAzureCredential | None = None
_cached_token: str | None = None
_token_expires: float = 0.0
_analyzer_ready: bool | None = None  # tri-state: None=not checked, True=ok, False=disabled


def _endpoint() -> str | None:
    """Return the AI Services endpoint, or None when CU is disabled."""
    return (os.environ.get("AZURE_AI_SERVICES_ENDPOINT") or "").rstrip("/") or None


async def _token() -> str:
    """Reuse a single DefaultAzureCredential and cache its token."""
    global _credential, _cached_token, _token_expires
    if _cached_token and time.time() < _token_expires - 60:
        return _cached_token
    if _credential is None:
        _credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    access = await _credential.get_token("https://cognitiveservices.azure.com/.default")
    _cached_token = access.token
    _token_expires = access.expires_on
    return _cached_token


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    endpoint = _endpoint()
    if endpoint is None:
        raise RuntimeError("AZURE_AI_SERVICES_ENDPOINT not configured")
    url = f"{endpoint}/contentunderstanding{path}"
    if "params" not in kwargs:
        kwargs["params"] = {}
    kwargs["params"].setdefault("api-version", API_VERSION)
    headers = kwargs.pop("headers", {}) or {}
    headers["Authorization"] = f"Bearer {await _token()}"
    async with httpx.AsyncClient(verify=False, timeout=120) as client:
        return await client.request(method, url, headers=headers, **kwargs)


async def _wait_for_analyzer_ready(timeout_s: int = 120) -> bool:
    """Poll the analyzer status until it transitions out of 'creating'."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = await _request("GET", f"/analyzers/{ANALYZER_ID}")
            if r.status_code == 200:
                status = (r.json().get("status") or "").lower()
                if status in ("ready", "succeeded", "completed", ""):
                    return True
                if status == "failed":
                    logger.error("Analyzer creation failed: %s", r.text[:300])
                    return False
                # Still creating — wait
            await asyncio.sleep(2.0)
        except Exception as e:  # noqa: BLE001
            logger.debug("Analyzer status poll: %s", e)
            await asyncio.sleep(2.0)
    logger.warning("Analyzer ready timeout")
    return False


async def ensure_analyzer() -> bool:
    """Create the custom analyzer on first call. Returns True if ready, False
    if Content Understanding is disabled (no endpoint configured).
    """
    global _analyzer_ready
    if _analyzer_ready is not None:
        return _analyzer_ready
    if _endpoint() is None:
        logger.info("Content Understanding disabled (AZURE_AI_SERVICES_ENDPOINT not set)")
        _analyzer_ready = False
        return False
    # GET to check existence first — avoids unnecessary PUTs.
    try:
        existing = await _request("GET", f"/analyzers/{ANALYZER_ID}")
        if existing.status_code == 200:
            status = (existing.json().get("status") or "").lower()
            if status in ("ready", "succeeded", "completed", ""):
                logger.info("Content Understanding analyzer '%s' already ready", ANALYZER_ID)
                _analyzer_ready = True
                return True
            # Exists but still being provisioned — wait it out.
            logger.info("Analyzer '%s' exists but status=%s, waiting...", ANALYZER_ID, status)
            if await _wait_for_analyzer_ready():
                _analyzer_ready = True
                return True
            _analyzer_ready = False
            return False
    except Exception as e:  # noqa: BLE001
        logger.warning("Content Understanding GET failed (will try create): %s", e)
    # Create
    body = {
        "baseAnalyzerId": BASE_ANALYZER_ID,
        "description": ACCIDENT_REPORT_SCHEMA["description"],
        "fieldSchema": {
            "name": ACCIDENT_REPORT_SCHEMA["name"],
            "fields": ACCIDENT_REPORT_SCHEMA["fields"],
        },
        "config": {"returnDetails": True, "enableOcr": True, "enableLayout": True},
    }
    try:
        created = await _request("PUT", f"/analyzers/{ANALYZER_ID}", json=body)
        if created.status_code not in (200, 201, 202):
            logger.error(
                "Content Understanding analyzer create failed %s: %s",
                created.status_code, created.text[:500],
            )
            _analyzer_ready = False
            return False
        # Creation may be async — poll the operation if a 202 came back.
        if created.status_code == 202 and (op_url := created.headers.get("operation-location")):
            await _poll_operation(op_url, label="analyzer-create")
        # Even with 201 the analyzer is not immediately usable — wait for ready.
        ok = await _wait_for_analyzer_ready()
        if not ok:
            _analyzer_ready = False
            return False
        logger.info("Content Understanding analyzer '%s' ready", ANALYZER_ID)
        _analyzer_ready = True
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Content Understanding analyzer create raised: %s", e)
        _analyzer_ready = False
        return False


async def _poll_operation(op_url: str, *, label: str = "operation", timeout_s: int = 60) -> dict | None:
    """Poll the operation-location URL until succeeded/failed/timeout."""
    headers = {"Authorization": f"Bearer {await _token()}"}
    deadline = time.time() + timeout_s
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        while time.time() < deadline:
            r = await client.get(op_url, headers=headers)
            if r.status_code != 200:
                logger.warning("%s poll %s: %s", label, r.status_code, r.text[:200])
                await asyncio.sleep(1.5)
                continue
            body = r.json()
            status = body.get("status", "").lower()
            if status in ("succeeded", "completed"):
                return body
            if status in ("failed", "canceled"):
                logger.error("%s ended with %s: %s", label, status, body)
                return None
            await asyncio.sleep(1.0)
    logger.warning("%s polling timed out after %ss", label, timeout_s)
    return None


def _flatten_fields(result: dict) -> dict[str, Any]:
    """Pull the `fields` dict out of the CU result envelope and unwrap the
    per-field shape (`{type, valueString, valueNumber, ...}`) into a plain
    mapping the rest of the pipeline can consume.
    """
    contents = result.get("result", {}).get("contents", [])
    if not contents:
        return {}
    fields = contents[0].get("fields", {}) or {}
    out: dict[str, Any] = {}
    for name, field in fields.items():
        if not isinstance(field, dict):
            out[name] = field
            continue
        for key in ("valueString", "valueNumber", "valueBoolean", "valueDate",
                    "valueTime", "valueArray", "valueObject", "content"):
            if key in field:
                out[name] = field[key]
                break
        else:
            out[name] = None
    return out


async def extract_from_bytes(blob: bytes, mime_type: str = "application/pdf") -> dict[str, Any]:
    """Analyze a binary file (PDF / image / audio) and return the flattened
    extracted fields. Raises if CU is not configured — callers should call
    ``ensure_analyzer()`` first and skip if it returns False.
    """
    if not await ensure_analyzer():
        raise RuntimeError("Content Understanding not configured")
    submit = await _request(
        "POST",
        f"/analyzers/{ANALYZER_ID}:analyze",
        content=blob,
        headers={"Content-Type": mime_type},
    )
    if submit.status_code not in (200, 202):
        raise RuntimeError(
            f"Content Understanding analyze submit {submit.status_code}: {submit.text[:300]}"
        )
    if submit.status_code == 202:
        op_url = submit.headers.get("operation-location")
        if not op_url:
            raise RuntimeError("Content Understanding returned 202 without operation-location")
        body = await _poll_operation(op_url, label="analyze", timeout_s=120)
        if body is None:
            raise RuntimeError("Content Understanding analyze did not complete")
    else:
        body = submit.json()
    return _flatten_fields(body)


async def extract_from_text(text: str) -> dict[str, Any]:
    """Convenience wrapper that submits plain text under the same analyzer.

    Useful when the customer types the claim into the dashboard textarea
    instead of attaching a document — we still want the schema-based
    extraction path so the rest of the pipeline has uniform input.
    """
    return await extract_from_bytes(text.encode("utf-8"), mime_type="text/plain")
