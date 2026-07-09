"""Create the Azure AI Search index for the SOP manuals and upload the chunks.

Uses the SAME chunking as the app's local retriever (``app.backend.rag.load_chunks``)
so the Azure AI Search path cites the exact same SOP documents as the local path.

Run after ``terraform apply`` (or let the ``infra`` terraform_data hook run it):

  $env:AZURE_SEARCH_ENDPOINT = "https://<search>.search.windows.net"
  $env:AZURE_SEARCH_INDEX    = "signal-to-service-sops"
  python scripts/seed_search_index.py

Auth: DefaultAzureCredential (az login). The caller needs the
``Search Index Data Contributor`` and ``Search Service Contributor`` roles on the
Search service (granted by infra/main.tf for the deploying principal).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make ``app.backend.rag`` importable when run from the demo root or scripts/.
DEMO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEMO_ROOT))

from app.backend.rag import load_chunks  # noqa: E402

from azure.identity import DefaultAzureCredential  # noqa: E402
from azure.search.documents import SearchClient  # noqa: E402
from azure.search.documents.indexes import SearchIndexClient  # noqa: E402
from azure.search.documents.indexes.models import (  # noqa: E402
    SearchableField,
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
)

ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
INDEX = os.getenv("AZURE_SEARCH_INDEX", "signal-to-service-sops")


def build_index() -> SearchIndex:
    return SearchIndex(
        name=INDEX,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="section", type=SearchFieldDataType.String),
            SimpleField(name="failure_mode", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="chunk", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String),
        ],
    )


def main() -> None:
    cred = DefaultAzureCredential()

    index_client = SearchIndexClient(endpoint=ENDPOINT, credential=cred)
    index_client.create_or_update_index(build_index())
    print(f"[seed] index '{INDEX}' created/updated")

    chunks = load_chunks()
    search_client = SearchClient(endpoint=ENDPOINT, index_name=INDEX, credential=cred)
    result = search_client.upload_documents(documents=chunks)
    ok = sum(1 for r in result if r.succeeded)
    print(f"[seed] uploaded {ok}/{len(chunks)} SOP chunks to '{INDEX}'")


if __name__ == "__main__":
    main()
