"""Analyze fabricated sample images with Azure Content Understanding."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentverse.content_understanding import ContentUnderstandingClient
from agentverse.contracts import AnalyzerKind, UploadedDocumentRequest
from agentverse.paths import CONTENT_UNDERSTANDING_RESULTS_DIR, FABRICATED_DOCUMENTS_DIR


def main() -> None:
    CONTENT_UNDERSTANDING_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for stale_result in CONTENT_UNDERSTANDING_RESULTS_DIR.glob("*.json"):
        stale_result.unlink()
    client = ContentUnderstandingClient()
    sample_paths = sorted([*FABRICATED_DOCUMENTS_DIR.glob("*.png"), *FABRICATED_DOCUMENTS_DIR.glob("*.pdf")])
    if not sample_paths:
        raise RuntimeError(f"No fabricated samples found in {FABRICATED_DOCUMENTS_DIR}")

    for image_path in sample_paths:
        content_type = "application/pdf" if image_path.suffix.lower() == ".pdf" else "image/png"
        result = client.analyze_upload(
            UploadedDocumentRequest(
                filename=image_path.name,
                content_type=content_type,
                content_bytes=image_path.read_bytes(),
                analyzer_kind=AnalyzerKind.AUTO,
            )
        )
        format_name = image_path.suffix.lower().lstrip(".")
        output_path = CONTENT_UNDERSTANDING_RESULTS_DIR / f"{image_path.stem}.{format_name}.{result.analyzer_id}.json"
        output_path.write_text(json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8")
        print(f"{image_path.name}: {len(result.markdown)} markdown chars via {result.analyzer_id} -> {output_path}")


if __name__ == "__main__":
    main()
