"""Hybrid BM25 plus local Chroma retrieval with reciprocal-rank fusion."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from rank_bm25 import BM25Okapi

from .config import settings

_TOKEN = re.compile("[A-Za-z0-9_]+")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source_file: str
    section_heading: str
    heading_hierarchy: str


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _heading(lines: list[str]) -> tuple[str, str]:
    headings = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    return (headings[-1] if headings else "Document", " > ".join(headings))


def _split_large(block: str, max_chars: int = 1500) -> list[str]:
    if len(block) <= max_chars:
        return [block.strip()]
    pieces: list[str] = []
    current: list[str] = []
    in_table = False
    for line in block.splitlines():
        is_table = line.lstrip().startswith("|")
        is_heading = line.startswith("##") and not is_table
        if is_heading and current and not in_table:
            pieces.append(chr(10).join(current).strip())
            current = []
        current.append(line)
        if is_table:
            in_table = True
        elif in_table and not line.strip():
            in_table = False
    if current:
        pieces.append(chr(10).join(current).strip())
    return [piece for piece in pieces if piece]


def load_chunks(kb_dir: Path | None = None) -> list[Chunk]:
    kb_dir = kb_dir or settings.root / "knowledge-base"
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for block in re.split("^[ \\t]*---[ \\t]*$", text, flags=re.MULTILINE):
            for piece in _split_large(block):
                if piece.strip():
                    heading, hierarchy = _heading(piece.splitlines())
                    source = path.relative_to(kb_dir.parent).as_posix()
                    cid = hashlib.sha256(f"{source}\n{piece}".encode()).hexdigest()
                    chunks.append(Chunk(cid, piece, source, heading, hierarchy))
    return chunks


class HybridRetriever:
    def __init__(self, chunks: list[Chunk] | None = None, *, persist_dir: Path | None = None):
        self.chunks = chunks or load_chunks()
        self.by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        self.bm25 = BM25Okapi([_tokens(c.text) for c in self.chunks])
        self.collection: Any = None
        self.collection_error = ""
        try:
            import chromadb
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            client = chromadb.PersistentClient(path=str(persist_dir or settings.chroma_dir))
            self.collection = client.get_or_create_collection(
                name="support_kb",
                embedding_function=cast(Any, DefaultEmbeddingFunction()),
                metadata={"hnsw:space": "cosine"},
            )
            self.collection.upsert(
                ids=[c.chunk_id for c in self.chunks],
                documents=[c.text for c in self.chunks],
                metadatas=[
                    {
                        "source_file": c.source_file,
                        "section_heading": c.section_heading,
                        "heading_hierarchy": c.heading_hierarchy,
                    }
                    for c in self.chunks
                ],
            )
        except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
            self.collection_error = str(exc)

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        try:
            scores = self.bm25.get_scores(_tokens(query))
            order = sorted(range(len(self.chunks)), key=lambda i: (-float(scores[i]), self.chunks[i].chunk_id))[
                : max(k * 4, 10)
            ]
        except (ValueError, IndexError, TypeError):
            order = list(range(min(max(k * 4, 10), len(self.chunks))))
        dense_ids: list[str] = []
        if self.collection is not None:
            try:
                result = self.collection.query(query_texts=[query], n_results=min(max(k * 4, 10), len(self.chunks)))
                dense_ids = result.get("ids", [[]])[0]
            except (OSError, RuntimeError, TypeError, ValueError):
                dense_ids = []
        fused: dict[str, float] = {}
        for rank, index in enumerate(order):
            fused[self.chunks[index].chunk_id] = fused.get(self.chunks[index].chunk_id, 0.0) + 1 / (60 + rank + 1)
        for rank, cid in enumerate(dense_ids):
            if cid in self.by_id:
                fused[cid] = fused.get(cid, 0.0) + 1 / (60 + rank + 1)
        ranked = sorted(fused, key=lambda cid: (-fused[cid], cid))[:k]
        return [{"chunk": self.by_id[cid], "score": fused[cid]} for cid in ranked]


_default: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _default
    if _default is None:
        _default = HybridRetriever()
    return _default
