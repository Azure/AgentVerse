"""Common filesystem paths used by the local playground."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FABRICATED_DOCUMENTS_DIR = DATA_DIR / "fabricated_documents"
CONTENT_UNDERSTANDING_RESULTS_DIR = DATA_DIR / "content_understanding_results"
SIMULATED_DB_PATH = DATA_DIR / "agentverse_simulated.db"
