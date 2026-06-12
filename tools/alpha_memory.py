from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any

from core.config import config

try:
    import chromadb
except Exception:  # pragma: no cover - optional dependency
    chromadb = None

logger = logging.getLogger(__name__)


class _JsonCollection:
    """Tiny file-backed replacement for the Chroma collection API used here."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, rows: List[Dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def add(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        rows = self._load()
        for document, metadata, row_id in zip(documents, metadatas, ids):
            rows.append({"id": row_id, "document": document, "metadata": metadata})
        self._save(rows)

    def query(self, query_texts: List[str], n_results: int = 3) -> Dict[str, Any]:
        query = (query_texts[0] if query_texts else "").lower()
        rows = self._load()
        scored = []
        query_terms = set(query.replace(",", " ").split())
        for row in rows:
            doc = str(row.get("document", "")).lower()
            metadata_text = json.dumps(row.get("metadata", {})).lower()
            haystack = set((doc + " " + metadata_text).replace(",", " ").split())
            overlap = len(query_terms & haystack)
            scored.append((overlap, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [row for _, row in scored[:n_results]]
        return {
            "documents": [[row.get("document") for row in selected]],
            "metadatas": [[row.get("metadata", {}) for row in selected]],
            "distances": [[1.0 / (1 + idx) for idx, _ in enumerate(selected)]],
        }


class AlphaMemoryClient:
    """Long-term strategy memory with Chroma when available, JSON fallback otherwise."""

    def __init__(self, persist_directory: str = "./alpha_memory"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = None
        if (not config.OFFLINE_MODE) and chromadb is not None:
            try:
                self.client = chromadb.PersistentClient(path=str(self.persist_directory))
                self.collection = self.client.get_or_create_collection(name="historical_strategies")
                return
            except Exception as exc:
                logger.warning("Chroma initialization failed; using JSON memory. Error: %s", exc)
        self.collection = _JsonCollection(self.persist_directory / "historical_strategies.json")

    def save_strategy(self, strategy_id: str, rationale: str, parameters: Dict[str, Any], results: Dict[str, Any]) -> None:
        try:
            metadata = {
                "strategy_id": strategy_id,
                "parameters": json.dumps(parameters),
                "results": json.dumps(results),
                "sharpe_ratio": float(results.get("sharpe_ratio", 0.0)),
            }
            self.collection.add(documents=[rationale], metadatas=[metadata], ids=[str(uuid.uuid4())])
            logger.info("Alpha Memory: saved strategy %s", strategy_id)
        except Exception as exc:
            logger.error("Alpha Memory: failed to save strategy. Error: %s", exc)

    def retrieve_similar_strategies(self, query_rationale: str, n_results: int = 3) -> List[Dict[str, Any]]:
        try:
            results = self.collection.query(query_texts=[query_rationale], n_results=n_results)
            output = []
            documents = results.get("documents") or [[]]
            metadatas = results.get("metadatas") or [[]]
            distances = results.get("distances") or [[]]
            for i, document in enumerate(documents[0]):
                output.append(
                    {
                        "rationale": document,
                        "metadata": metadatas[0][i] if i < len(metadatas[0]) else {},
                        "distance": distances[0][i] if i < len(distances[0]) else None,
                    }
                )
            return output
        except Exception as exc:
            logger.warning("Alpha Memory: retrieval failed or empty. Error: %s", exc)
            return []


alpha_memory = AlphaMemoryClient()
