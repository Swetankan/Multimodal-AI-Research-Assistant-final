from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class RetrievedChunk:
    id: str
    text: str
    score: float
    dense_score: float = 0.0
    lexical_score: float = 0.0
    bm25_score: float = 0.0
    rerank_score: float = 0.0
    document_id: str = ""
    filename: str = ""
    page: int = 0
    chunk_id: int = 0
    source_type: str = "text"


_ENCODER_CACHE: dict[str, SentenceTransformer] = {}


class FaissVectorStore:
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/paraphrase-MiniLM-L3-v2",
        storage_dir: str | Path = "storage"
    ) -> None:
        self.embedding_model_name = embedding_model
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "faiss.index"
        self.metadata_path = self.storage_dir / "chunks.json"
        self.index: faiss.IndexFlatIP | None = None
        self.chunks: list[RetrievedChunk] = []
        self.load()

    def clear(self) -> None:
        self.index = None
        self.chunks = []
        self._delete_persisted_files()

    def _delete_persisted_files(self) -> None:
        self.index_path.unlink(missing_ok=True)
        self.metadata_path.unlink(missing_ok=True)

    def _get_encoder(self) -> SentenceTransformer:
        if self.embedding_model_name not in _ENCODER_CACHE:
            _ENCODER_CACHE[self.embedding_model_name] = SentenceTransformer(self.embedding_model_name)
        return _ENCODER_CACHE[self.embedding_model_name]

    def _embed(self, texts: Iterable[str]) -> np.ndarray:
        embeddings = self._get_encoder().encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return np.asarray(embeddings, dtype="float32")

    def add_texts(
        self,
        texts: list[str],
        document_id: str = "",
        filename: str = "",
        pages: list[int] | None = None,
        source_types: list[str] | None = None
    ) -> int:
        if not texts:
            return 0

        embeddings = self._embed(texts)
        if self.index is None:
            self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        for offset, text in enumerate(texts, start=1):
            chunk_id = offset
            chunk_key = f"{document_id}-chunk-{chunk_id}" if document_id else f"chunk-{len(self.chunks) + 1}"
            page = pages[offset - 1] if pages and offset <= len(pages) else 0
            source_type = source_types[offset - 1] if source_types and offset <= len(source_types) else "text"
            self.chunks.append(
                RetrievedChunk(
                    id=chunk_key,
                    text=text,
                    score=0.0,
                    document_id=document_id,
                    filename=filename,
                    page=page,
                    chunk_id=chunk_id,
                    source_type=source_type,
                )
            )
        self.save()
        return len(texts)

    def save(self) -> None:
        if self.index is None:
            return

        faiss.write_index(self.index, str(self.index_path))
        payload = {
            "embedding_model": self.embedding_model_name,
            "chunks": [asdict(chunk) for chunk in self.chunks]
        }
        self.metadata_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def load(self) -> bool:
        if not self.index_path.exists() or not self.metadata_path.exists():
            return False

        self.index = faiss.read_index(str(self.index_path))
        payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self.embedding_model_name = payload.get("embedding_model", self.embedding_model_name)
        self.chunks = [RetrievedChunk(**item) for item in payload.get("chunks", [])]
        return bool(self.chunks)

    def search(
        self,
        query: str,
        top_k: int = 4,
        oversample_factor: int = 3,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None
    ) -> list[RetrievedChunk]:
        if self.index is None or not self.chunks:
            return []

        query_embedding = self._embed([query])
        document_filter = {item for item in (document_ids or []) if item}
        pool_size = candidate_pool_size or max(top_k * oversample_factor, top_k)
        search_k = len(self.chunks) if document_filter else min(pool_size, len(self.chunks))
        scores, indices = self.index.search(query_embedding, search_k)

        candidate_scores: dict[int, dict[str, float]] = {}
        for dense_score, index in zip(scores[0], indices[0]):
            if index < 0:
                continue
            chunk = self.chunks[index]
            if document_filter and chunk.document_id not in document_filter:
                continue
            candidate_scores[int(index)] = {
                "dense_score": float(dense_score),
                "bm25_score": 0.0,
            }

        for index, bm25_score in self._bm25_search(query, document_filter, pool_size):
            current = candidate_scores.setdefault(
                index,
                {"dense_score": 0.0, "bm25_score": 0.0}
            )
            current["bm25_score"] = bm25_score

        max_bm25 = max((item["bm25_score"] for item in candidate_scores.values()), default=0.0)
        weighted_candidates: list[RetrievedChunk] = []
        for index, scores_by_type in candidate_scores.items():
            chunk = self.chunks[index]
            dense_score = scores_by_type["dense_score"]
            bm25_score = scores_by_type["bm25_score"]
            normalized_dense = self._normalize_dense_score(dense_score)
            normalized_bm25 = (bm25_score / max_bm25) if max_bm25 > 0 else 0.0
            final_score = (dense_weight * normalized_dense) + (bm25_weight * normalized_bm25)
            weighted_candidates.append(
                RetrievedChunk(
                    id=chunk.id,
                    text=chunk.text,
                    score=final_score,
                    dense_score=dense_score,
                    lexical_score=normalized_bm25,
                    bm25_score=bm25_score,
                    rerank_score=0.0,
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    page=chunk.page,
                    chunk_id=chunk.chunk_id,
                    source_type=chunk.source_type,
                )
            )

        ranked = sorted(
            weighted_candidates,
            key=lambda item: (item.score, item.bm25_score, item.dense_score),
            reverse=True
        )
        return ranked[:top_k]

    def delete_document(self, document_id: str) -> int:
        remaining = [chunk for chunk in self.chunks if chunk.document_id != document_id]
        removed_count = len(self.chunks) - len(remaining)
        if removed_count == 0:
            return 0

        self.chunks = remaining
        if not self.chunks:
            self.clear()
            return removed_count

        embeddings = self._embed([chunk.text for chunk in self.chunks])
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        self.save()
        return removed_count

    def has_documents(self) -> bool:
        return bool(self.chunks)

    def document_count(self) -> int:
        return len(self.chunks)

    def describe(self) -> dict[str, str | int | bool]:
        return {
            "storage_dir": str(self.storage_dir),
            "index_path": str(self.index_path),
            "metadata_path": str(self.metadata_path),
            "chunks_indexed": len(self.chunks),
            "persisted": self.index_path.exists() and self.metadata_path.exists(),
            "embedding_model": self.embedding_model_name,
            "encoder_loaded": self.embedding_model_name in _ENCODER_CACHE,
        }

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            token
            for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
            if len(token) > 2
        ]

    def _bm25_search(
        self,
        query: str,
        document_filter: set[str],
        pool_size: int
    ) -> list[tuple[int, float]]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        searchable = [
            (index, chunk)
            for index, chunk in enumerate(self.chunks)
            if not document_filter or chunk.document_id in document_filter
        ]
        if not searchable:
            return []

        tokenized_chunks = [
            (index, Counter(self._tokenize(chunk.text)))
            for index, chunk in searchable
        ]
        doc_lengths = [sum(term_counts.values()) for _, term_counts in tokenized_chunks]
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
        if avg_doc_length == 0:
            return []

        doc_frequency: Counter[str] = Counter()
        for _, term_counts in tokenized_chunks:
            for term in set(term_counts):
                doc_frequency[term] += 1

        total_docs = len(tokenized_chunks)
        k1 = 1.5
        b = 0.75
        results: list[tuple[int, float]] = []

        for (index, term_counts), doc_length in zip(tokenized_chunks, doc_lengths):
            score = 0.0
            for term in query_terms:
                term_frequency = term_counts.get(term, 0)
                if term_frequency == 0:
                    continue
                idf = math.log(1 + ((total_docs - doc_frequency[term] + 0.5) / (doc_frequency[term] + 0.5)))
                denominator = term_frequency + k1 * (1 - b + b * (doc_length / avg_doc_length))
                score += idf * ((term_frequency * (k1 + 1)) / denominator)
            if score > 0:
                results.append((index, score))

        return sorted(results, key=lambda item: item[1], reverse=True)[:pool_size]

    @staticmethod
    def _normalize_dense_score(score: float) -> float:
        return max(0.0, min((score + 1.0) / 2.0, 1.0))
