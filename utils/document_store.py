"""Per-conversation document storage: chunks, embeddings and search."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from utils.document_processing import Chunk

DOCUMENTS_DIRNAME = "documents"
_DOC_ID_RE = re.compile(r"^[0-9a-f]{12}$")


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    document_name: str
    chunk_index: int  # 0-based
    chunk_count: int
    page: int | None
    text: str
    score: float


class DocumentStore:
    """Documents of one session, stored inside that session's directory."""

    def __init__(self, session_dir: str | Path) -> None:
        self.root = Path(session_dir) / DOCUMENTS_DIRNAME

    def list_documents(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []

        documents = []

        for directory in self.root.iterdir():
            # Temporary ".tmp-..." folders do not match and are skipped.
            if not directory.is_dir() or not _DOC_ID_RE.match(directory.name):
                continue

            try:
                meta = json.loads(
                    (directory / "meta.json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                continue

            if isinstance(meta, dict) and "name" in meta:
                documents.append(meta)

        documents.sort(
            key=lambda item: (item.get("uploaded_at", ""), item["name"])
        )
        return documents

    def has_documents(self) -> bool:
        return bool(self.list_documents())

    def add(
        self,
        name: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
        embedding_model: str,
        size_bytes: int = 0,
        pages: int | None = None,
    ) -> dict[str, Any]:
        matrix = np.asarray(vectors, dtype=np.float32)

        if matrix.ndim != 2 or matrix.shape[0] != len(chunks) or not chunks:
            raise ValueError("The embeddings do not match the chunks.")

        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        matrix = matrix / norms

        doc_id = uuid.uuid4().hex[:12]
        meta = {
            "id": doc_id,
            "name": name,
            "chunk_count": len(chunks),
            "char_count": sum(len(chunk.text) for chunk in chunks),
            "pages": pages,
            "size_bytes": size_bytes,
            "embedding_model": embedding_model,
            "uploaded_at": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
        }

        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.root / f".tmp-{doc_id}"
        final = self.root / doc_id

        try:
            temporary.mkdir()
            (temporary / "chunks.json").write_text(
                json.dumps(
                    [{"text": c.text, "page": c.page} for c in chunks],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            np.save(temporary / "vectors.npy", matrix)
            (temporary / "meta.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary.replace(final)
        except BaseException:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

        return meta

    def remove(self, document_id: str) -> bool:
        if not _DOC_ID_RE.match(document_id):
            return False

        directory = self.root / document_id

        if not directory.is_dir():
            return False

        shutil.rmtree(directory)
        return True

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        embedding_model: str,
        document_ids: set[str] | None = None,
    ) -> tuple[list[SearchHit], list[str]]:
        """Return the best chunks and the names of documents that could
        not be searched (embedded with another model, or unreadable)."""
        query = np.asarray(query_vector, dtype=np.float32)
        norm = float(np.linalg.norm(query))

        if query.ndim != 1 or norm == 0:
            return [], []

        query = query / norm

        candidates: list[tuple[float, dict[str, Any], int]] = []
        skipped: list[str] = []

        for meta in self.list_documents():
            if document_ids is not None and meta["id"] not in document_ids:
                continue

            try:
                matrix = np.load(self.root / meta["id"] / "vectors.npy")
            except (OSError, ValueError):
                skipped.append(meta["name"])
                continue

            if (
                meta.get("embedding_model") != embedding_model
                or matrix.ndim != 2
                or matrix.shape[1] != query.shape[0]
            ):
                skipped.append(meta["name"])
                continue

            scores = matrix @ query
            best = np.argsort(scores)[::-1][:top_k]
            candidates.extend((float(scores[i]), meta, int(i)) for i in best)

        candidates.sort(key=lambda item: item[0], reverse=True)

        chunk_cache: dict[str, list[dict[str, Any]]] = {}
        hits: list[SearchHit] = []

        for score, meta, index in candidates[:top_k]:
            chunks = chunk_cache.get(meta["id"])

            if chunks is None:
                try:
                    chunks = json.loads(
                        (self.root / meta["id"] / "chunks.json").read_text(
                            encoding="utf-8"
                        )
                    )
                except (OSError, ValueError):
                    chunks = []

                chunk_cache[meta["id"]] = chunks

            if index >= len(chunks):
                continue

            chunk = chunks[index]
            hits.append(
                SearchHit(
                    document_id=meta["id"],
                    document_name=meta["name"],
                    chunk_index=index,
                    chunk_count=meta["chunk_count"],
                    page=chunk.get("page"),
                    text=chunk["text"],
                    score=score,
                )
            )

        return hits, skipped