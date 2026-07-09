"""Retrieval layer for SOP manuals — the RAG grounding of the Knowledge agent.

A single abstraction, ``retrieve_sop(query, failure_mode)``, is served by two
interchangeable backends that return the **identical** result contract:

    [{ "doc_id", "title", "chunk", "source", "score", "failure_mode" }]

  * ``LocalRag``       — pure-Python TF-IDF cosine over the bundled SOP markdown.
                         No external service required (this is the local-first path).
  * ``AzureSearchRag`` — the same SOP chunks indexed in Azure AI Search, queried
                         over the same schema. Used when ``AZURE_SEARCH_ENDPOINT``
                         is configured.

Both backends share the same document IDs and chunking so the demo cites the
same SOP locally and after deployment.
"""
from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

SOPS_DIR = Path(__file__).resolve().parent.parent / "data" / "sops"

# ---------------------------------------------------------------------------
# Shared corpus loading + chunking (used by BOTH backends and the index seeder)
# ---------------------------------------------------------------------------

_FRONT = re.compile(r"^---\s*(.*?)\s*---\s*(.*)$", re.DOTALL)
_TOKEN = re.compile(r"[a-z0-9]+")


def _parse_front_matter(text: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    m = _FRONT.match(text)
    body = text
    if m:
        raw, body = m.group(1), m.group(2)
        for line in raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    meta["_body"] = body
    return meta


def load_chunks() -> List[Dict[str, Any]]:
    """Chunk every SOP by ``## `` section. One chunk = one procedure section."""
    chunks: List[Dict[str, Any]] = []
    for path in sorted(SOPS_DIR.glob("*.md")):
        meta = _parse_front_matter(path.read_text(encoding="utf-8"))
        sop_id = meta.get("sop_id", path.stem)
        title = meta.get("title", sop_id)
        failure_mode = meta.get("failure_mode", "")
        body = meta.get("_body", "")
        # Split on level-2 headings, keeping the heading with its section.
        parts = re.split(r"(?m)^##\s+", body)
        section_idx = 0
        for part in parts:
            part = part.strip()
            if not part or part.startswith("#"):
                continue
            section_idx += 1
            heading = part.splitlines()[0].strip()
            chunks.append({
                "id": f"{sop_id}::{section_idx}",
                "doc_id": sop_id,
                "title": title,
                "section": heading,
                "failure_mode": failure_mode,
                "chunk": part,
                "source": path.name,
            })
    return chunks


def _tokenize(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


# ---------------------------------------------------------------------------
# Local TF-IDF backend
# ---------------------------------------------------------------------------

class LocalRag:
    def __init__(self) -> None:
        self.chunks = load_chunks()
        self._docs_tokens = [_tokenize(c["section"] + " " + c["chunk"]) for c in self.chunks]
        n = len(self.chunks)
        df: Counter = Counter()
        for toks in self._docs_tokens:
            for term in set(toks):
                df[term] += 1
        self._idf = {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}
        self._doc_vectors = [self._vectorize(toks) for toks in self._docs_tokens]

    def _vectorize(self, tokens: List[str]) -> Dict[str, float]:
        tf = Counter(tokens)
        vec = {t: (c / len(tokens)) * self._idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def _cosine(self, q: Dict[str, float], d: Dict[str, float]) -> float:
        # Iterate the smaller vector for speed.
        if len(q) > len(d):
            q, d = d, q
        return sum(v * d.get(t, 0.0) for t, v in q.items())

    def retrieve(self, query: str, failure_mode: str = "", top_k: int = 3) -> List[Dict[str, Any]]:
        qvec = self._vectorize(_tokenize(query + " " + failure_mode))
        scored = []
        for chunk, dvec in zip(self.chunks, self._doc_vectors):
            score = self._cosine(qvec, dvec)
            if failure_mode and chunk.get("failure_mode") == failure_mode:
                score += 0.35  # strong prior: exact failure-mode match
            scored.append((score, chunk))
        scored.sort(key=lambda s: s[0], reverse=True)
        out = []
        for score, chunk in scored[:top_k]:
            item = {k: chunk[k] for k in ("doc_id", "title", "chunk", "source", "failure_mode", "section")}
            item["score"] = round(float(score), 4)
            out.append(item)
        return out


# ---------------------------------------------------------------------------
# Azure AI Search backend
# ---------------------------------------------------------------------------

class AzureSearchRag:
    def __init__(self, endpoint: str, index: str) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.search.documents import SearchClient
        self._client = SearchClient(
            endpoint=endpoint, index_name=index, credential=DefaultAzureCredential()
        )

    def retrieve(self, query: str, failure_mode: str = "", top_k: int = 3) -> List[Dict[str, Any]]:
        search_text = f"{query} {failure_mode}".strip()
        results = self._client.search(search_text=search_text, top=top_k)
        out = []
        for r in results:
            out.append({
                "doc_id": r.get("doc_id"),
                "title": r.get("title"),
                "chunk": r.get("chunk"),
                "source": r.get("source"),
                "failure_mode": r.get("failure_mode"),
                "section": r.get("section"),
                "score": round(float(r.get("@search.score", 0.0)), 4),
            })
        return out


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_backend: Optional[Any] = None
_backend_kind: str = "local"


def get_backend() -> Any:
    global _backend, _backend_kind
    if _backend is not None:
        return _backend
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
    index = os.getenv("AZURE_SEARCH_INDEX", "signal-to-service-sops").strip()
    if endpoint:
        try:
            _backend = AzureSearchRag(endpoint, index)
            _backend_kind = "azure-ai-search"
            return _backend
        except Exception as ex:  # pragma: no cover - falls back to local
            print(f"[rag] Azure AI Search unavailable ({ex}); using local TF-IDF")
    _backend = LocalRag()
    _backend_kind = "local"
    return _backend


def backend_kind() -> str:
    get_backend()
    return _backend_kind


def retrieve_sop(query: str, failure_mode: str = "", top_k: int = 3) -> List[Dict[str, Any]]:
    return get_backend().retrieve(query, failure_mode=failure_mode, top_k=top_k)
