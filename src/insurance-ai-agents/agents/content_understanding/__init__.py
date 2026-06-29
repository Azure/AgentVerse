"""Azure AI Content Understanding adapter for the claims-intake pipeline.

This package wraps the Azure AI Content Understanding REST API
(/contentunderstanding/analyzers) so the rest of the codebase can:

  1) Lazily create a custom analyzer for the Spanish "parte de siniestro" the
     first time it is needed (`ensure_analyzer()`).
  2) Extract structured fields from a document, image or audio file with a
     single async call (`extract_from_bytes()`).

The analyzer is created on the existing AI Services account
(``AZURE_AI_SERVICES_ENDPOINT``) using a Pro-mode (multimodal) base analyzer
so the same definition handles photos, PDFs, scans and short audio notes the
customer may attach to the claim.

The intake pipeline (``agents/claims-intake/agent.py``) calls this as a fast
deterministic first pass and lets the LLM enrich / validate the result.
"""

from .agent import (
    ensure_analyzer,
    extract_from_bytes,
    extract_from_text,
    ANALYZER_ID,
    PARTE_SINIESTRO_SCHEMA,
)

__all__ = [
    "ensure_analyzer",
    "extract_from_bytes",
    "extract_from_text",
    "ANALYZER_ID",
    "PARTE_SINIESTRO_SCHEMA",
]
