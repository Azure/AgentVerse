"""Claims persistence in Azure Cosmos DB.

Design:
- Container `claims` partitioned by `/customer_id`
- AAD access with DefaultAzureCredential (keyless)
- If the COSMOS_* environment variables are not configured, the repository
  falls back to no-op mode so the backend keeps working locally without Cosmos.

When Cosmos is active, the backend persists each processed claim for:
- Customer view: list "my claims" (query by partition key)
- Operator view: human review queue (cross-partition query by decision)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _ensure_azure_cli_on_path() -> None:
    """Ensure `az.cmd` is on PATH so AzureCliCredential can find it.

    On Windows, when uvicorn is started as a detached process, sometimes the
    inherited PATH does not include the Azure CLI directory even though the
    user has it installed. azure-identity invokes `az` via subprocess, so
    without the directory on PATH, AzureCliCredential fails with
    'Failed to invoke the Azure CLI'.
    """
    if sys.platform != "win32":
        return
    candidates = [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin",
        r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin",
    ]
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep)
    for c in candidates:
        if os.path.isfile(os.path.join(c, "az.cmd")) and c not in parts:
            os.environ["PATH"] = c + os.pathsep + current
            current = os.environ["PATH"]
            parts = current.split(os.pathsep)


class ClaimsRepository:
    """Wrapper over the Cosmos DB `claims` container."""

    def __init__(self) -> None:
        self.endpoint = os.environ.get("COSMOS_ENDPOINT", "").strip()
        self.database_name = os.environ.get("COSMOS_DATABASE", "insurance-claims")
        self.container_name = os.environ.get("COSMOS_CONTAINER", "claims")
        self._container = None
        self._client = None

        if not self.endpoint:
            logger.info("Cosmos DB not configured (COSMOS_ENDPOINT empty) → in-memory mode.")
            return

        _ensure_azure_cli_on_path()

        try:
            from azure.cosmos import CosmosClient
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            self._client = CosmosClient(self.endpoint, credential=credential)
            db = self._client.get_database_client(self.database_name)
            self._container = db.get_container_client(self.container_name)
            logger.info(
                "Cosmos DB connected: endpoint=%s db=%s container=%s",
                self.endpoint, self.database_name, self.container_name,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not connect to Cosmos DB (%s) → in-memory mode.", e)
            self._container = None

    @property
    def is_enabled(self) -> bool:
        return self._container is not None

    def save(self, claim: dict[str, Any]) -> None:
        """Persist a processed claim. No-op if Cosmos is not active."""
        if not self._container:
            return
        # Cosmos requires `id` as a string and `customer_id` for the partition key
        doc = dict(claim)
        doc["id"] = doc.get("claim_id") or doc["id"]
        if "customer_id" not in doc:
            inp = doc.get("_input", {}) or {}
            doc["customer_id"] = inp.get("customer_id", "unknown")
        doc["persisted_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self._container.upsert_item(doc)
            logger.debug("Cosmos upsert ok: id=%s customer=%s", doc["id"], doc["customer_id"])
        except Exception as e:  # noqa: BLE001
            logger.warning("Cosmos upsert failed (id=%s): %s", doc.get("id"), e)

    def get(self, claim_id: str, customer_id: str) -> Optional[dict[str, Any]]:
        if not self._container:
            return None
        try:
            return self._container.read_item(item=claim_id, partition_key=customer_id)
        except Exception as e:  # noqa: BLE001
            logger.debug("Cosmos read failed (id=%s): %s", claim_id, e)
            return None

    def list_by_customer(self, customer_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Query by partition key — efficient, single-partition."""
        if not self._container:
            return []
        try:
            items = list(self._container.query_items(
                query="SELECT * FROM c WHERE c.customer_id = @cid ORDER BY c.timestamp DESC OFFSET 0 LIMIT @lim",
                parameters=[{"name": "@cid", "value": customer_id}, {"name": "@lim", "value": limit}],
                partition_key=customer_id,
            ))
            return items
        except Exception as e:  # noqa: BLE001
            logger.warning("Cosmos query (by customer) failed: %s", e)
            return []

    def list_pending_review(self, limit: int = 100) -> list[dict[str, Any]]:
        """Human review queue — cross-partition (operator use)."""
        if not self._container:
            return []
        try:
            items = list(self._container.query_items(
                query="SELECT * FROM c WHERE c.decision = 'human_review' ORDER BY c.timestamp DESC OFFSET 0 LIMIT @lim",
                parameters=[{"name": "@lim", "value": limit}],
                enable_cross_partition_query=True,
            ))
            return items
        except Exception as e:  # noqa: BLE001
            logger.warning("Cosmos query (pending review) failed: %s", e)
            return []

    def list_all(self, limit: int = 200) -> list[dict[str, Any]]:
        """List all claims — cross-partition (operator use)."""
        if not self._container:
            return []
        try:
            items = list(self._container.query_items(
                query="SELECT * FROM c ORDER BY c.timestamp DESC OFFSET 0 LIMIT @lim",
                parameters=[{"name": "@lim", "value": limit}],
                enable_cross_partition_query=True,
            ))
            return items
        except Exception as e:  # noqa: BLE001
            logger.warning("Cosmos query (all) failed: %s", e)
            return []


# Singleton — instantiated only once on import
_repo: ClaimsRepository | None = None


def get_repo() -> ClaimsRepository:
    global _repo
    if _repo is None:
        _repo = ClaimsRepository()
    return _repo
