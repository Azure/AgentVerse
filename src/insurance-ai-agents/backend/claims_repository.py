"""Persistencia de siniestros en Azure Cosmos DB.

Diseño:
- Container `claims` particionado por `/customer_id`
- Acceso AAD con DefaultAzureCredential (sin claves)
- Si las variables de entorno COSMOS_* no están configuradas, el repositorio
  cae en modo no-op para que el backend siga funcionando en local sin Cosmos.

Cuando Cosmos está activo, el backend persiste cada siniestro procesado para:
- Vista de Cliente: listar "mis siniestros" (query por partition key)
- Vista de Operario: cola de revisión humana (query cross-partition por decision)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _ensure_azure_cli_on_path() -> None:
    """Asegura que `az.cmd` está en PATH para que AzureCliCredential lo encuentre.

    En Windows, cuando uvicorn se arranca como proceso desligado, a veces el
    PATH heredado no incluye el directorio de Azure CLI aunque el usuario lo
    tenga instalado. azure-identity invoca `az` por subprocess, así que sin
    el directorio en PATH, AzureCliCredential falla con
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
    """Wrapper sobre el container `claims` de Cosmos DB."""

    def __init__(self) -> None:
        self.endpoint = os.environ.get("COSMOS_ENDPOINT", "").strip()
        self.database_name = os.environ.get("COSMOS_DATABASE", "insurance-claims")
        self.container_name = os.environ.get("COSMOS_CONTAINER", "claims")
        self._container = None
        self._client = None

        if not self.endpoint:
            logger.info("Cosmos DB no configurado (COSMOS_ENDPOINT vacío) → modo en-memoria.")
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
                "Cosmos DB conectado: endpoint=%s db=%s container=%s",
                self.endpoint, self.database_name, self.container_name,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("No se pudo conectar a Cosmos DB (%s) → modo en-memoria.", e)
            self._container = None

    @property
    def is_enabled(self) -> bool:
        return self._container is not None

    def save(self, claim: dict[str, Any]) -> None:
        """Persiste un siniestro procesado. No-op si Cosmos no está activo."""
        if not self._container:
            return
        # Cosmos requiere `id` como string y `customer_id` para el partition key
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
            logger.warning("Cosmos upsert falló (id=%s): %s", doc.get("id"), e)

    def get(self, claim_id: str, customer_id: str) -> Optional[dict[str, Any]]:
        if not self._container:
            return None
        try:
            return self._container.read_item(item=claim_id, partition_key=customer_id)
        except Exception as e:  # noqa: BLE001
            logger.debug("Cosmos read falló (id=%s): %s", claim_id, e)
            return None

    def list_by_customer(self, customer_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Query por partition key — eficiente, single-partition."""
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
            logger.warning("Cosmos query (by customer) falló: %s", e)
            return []

    def list_pending_review(self, limit: int = 100) -> list[dict[str, Any]]:
        """Cola de revisión humana — cross-partition (uso operario)."""
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
            logger.warning("Cosmos query (pending review) falló: %s", e)
            return []

    def list_all(self, limit: int = 200) -> list[dict[str, Any]]:
        """Lista todos los siniestros — cross-partition (uso operario)."""
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
            logger.warning("Cosmos query (all) falló: %s", e)
            return []


# Singleton — se instancia una sola vez al importar
_repo: ClaimsRepository | None = None


def get_repo() -> ClaimsRepository:
    global _repo
    if _repo is None:
        _repo = ClaimsRepository()
    return _repo
