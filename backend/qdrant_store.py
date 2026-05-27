import os
import json
import math
import re
import uuid
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from vector_store import RetrievedChunk, _ENCODER_CACHE

class QdrantVectorStore:
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/paraphrase-MiniLM-L3-v2",
        storage_dir: str | Path = "storage"
    ) -> None:
        self.embedding_model_name = embedding_model
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Connect to hosted Qdrant cloud or run locally in-memory/on-disk
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if qdrant_url:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            self.is_local = False
        else:
            # Embedded local persistent storage engine
            qdrant_db_path = self.storage_dir / "qdrant"
            self.client = QdrantClient(path=str(qdrant_db_path))
            self.is_local = True
            
        self.collection_name = "research_assistant_chunks"
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> None:
        dim = 384
        if "all-MiniLM-L6" in self.embedding_model_name:
            dim = 384
        
        collections_resp = self.client.get_collections()
        exists = any(col.name == self.collection_name for col in collections_resp.collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def _get_encoder(self):
        if self.embedding_model_name not in _ENCODER_CACHE:
            from sentence_transformers import SentenceTransformer
            _ENCODER_CACHE[self.embedding_model_name] = SentenceTransformer(self.embedding_model_name)
        return _ENCODER_CACHE[self.embedding_model_name]

    def _embed(self, texts: Iterable[str]) -> list[list[float]]:
        embeddings = self._get_encoder().encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.tolist()

    def clear(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._ensure_collection_exists()

    @property
    def chunks(self) -> list[RetrievedChunk]:
        return self._get_all_chunks(set())

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
        points = []
        for offset, (text, embedding) in enumerate(zip(texts, embeddings), start=1):
            chunk_id = offset
            chunk_key = f"{document_id}-chunk-{chunk_id}" if document_id else f"chunk-{offset}"
            page = pages[offset - 1] if pages and offset <= len(pages) else 0
            source_type = source_types[offset - 1] if source_types and offset <= len(source_types) else "text"
            
            # Deterministic namespace UUID from chunk key (Qdrant requires int/UUID-like strings)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_key))
            
            payload = {
                "chunk_key": chunk_key,
                "text": text,
                "document_id": document_id,
                "filename": filename,
                "page": page,
                "chunk_id": chunk_id,
                "source_type": source_type
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        return len(texts)

    def delete_document(self, document_id: str) -> int:
        count_before = self.document_count()
        
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
        )
        
        count_after = self.document_count()
        return max(0, count_before - count_after)

    def has_documents(self) -> bool:
        return self.document_count() > 0

    def document_count(self) -> int:
        resp = self.client.count(collection_name=self.collection_name)
        return resp.count

    def describe(self) -> dict[str, str | int | bool]:
        col_info = self.client.get_collection(collection_name=self.collection_name)
        return {
            "storage_dir": str(self.storage_dir),
            "collection_name": self.collection_name,
            "chunks_indexed": col_info.points_count,
            "persisted": True,
            "embedding_model": self.embedding_model_name,
            "encoder_loaded": self.embedding_model_name in _ENCODER_CACHE,
            "provider": "qdrant",
            "is_local": self.is_local
        }

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            token
            for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
            if len(token) > 2
        ]

    def _get_all_chunks(self, document_filter: set[str]) -> list[RetrievedChunk]:
        chunks = []
        offset = None
        while True:
            scroll_filter = None
            if document_filter:
                conditions = [
                    FieldCondition(key="document_id", match=MatchValue(value=doc_id))
                    for doc_id in document_filter
                ]
                scroll_filter = Filter(should=conditions)
                
            resp, next_page = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=100,
                with_payload=True,
                with_vectors=False,
                offset=offset
            )
            for point in resp:
                p = point.payload
                chunks.append(
                    RetrievedChunk(
                        id=p.get("chunk_key", point.id),
                        text=p.get("text", ""),
                        score=0.0,
                        document_id=p.get("document_id", ""),
                        filename=p.get("filename", ""),
                        page=p.get("page", 0),
                        chunk_id=p.get("chunk_id", 0),
                        source_type=p.get("source_type", "text")
                    )
                )
            if not next_page:
                break
            offset = next_page
        return chunks

    def _bm25_search(
        self,
        query: str,
        document_filter: set[str],
        pool_size: int
    ) -> list[tuple[int, float, RetrievedChunk]]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        all_chunks = self._get_all_chunks(document_filter)
        if not all_chunks:
            return []

        tokenized_chunks = [
            (i, Counter(self._tokenize(chunk.text)), chunk)
            for i, chunk in enumerate(all_chunks)
        ]
        doc_lengths = [sum(term_counts.values()) for _, term_counts, _ in tokenized_chunks]
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
        if avg_doc_length == 0:
            return []

        doc_frequency: Counter[str] = Counter()
        for _, term_counts, _ in tokenized_chunks:
            for term in set(term_counts):
                doc_frequency[term] += 1

        total_docs = len(tokenized_chunks)
        k1 = 1.5
        b = 0.75
        results: list[tuple[int, float, RetrievedChunk]] = []

        for (idx, term_counts, chunk), doc_length in zip(tokenized_chunks, doc_lengths):
            score = 0.0
            for term in query_terms:
                term_frequency = term_counts.get(term, 0)
                if term_frequency == 0:
                    continue
                idf = math.log(1 + ((total_docs - doc_frequency[term] + 0.5) / (doc_frequency[term] + 0.5)))
                denominator = term_frequency + k1 * (1 - b + b * (doc_length / avg_doc_length))
                score += idf * ((term_frequency * (k1 + 1)) / denominator)
            if score > 0:
                results.append((idx, score, chunk))

        sorted_results = sorted(results, key=lambda item: item[1], reverse=True)[:pool_size]
        return sorted_results

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
        query_vector = self._embed([query])[0]
        document_filter = {item for item in (document_ids or []) if item}
        
        qdrant_filter = None
        if document_filter:
            conditions = [
                FieldCondition(key="document_id", match=MatchValue(value=doc_id))
                for doc_id in document_filter
            ]
            qdrant_filter = Filter(should=conditions)

        pool_size = candidate_pool_size or max(top_k * oversample_factor, top_k)
        
        total_count = self.document_count()
        if total_count == 0:
            return []
            
        search_k = min(pool_size, total_count)
        
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=search_k,
            with_payload=True
        )

        candidate_scores: dict[str, dict[str, Any]] = {}
        for hit in search_results:
            p = hit.payload
            chunk_key = p.get("chunk_key") or hit.id
            chunk = RetrievedChunk(
                id=chunk_key,
                text=p.get("text", ""),
                score=0.0,
                document_id=p.get("document_id", ""),
                filename=p.get("filename", ""),
                page=p.get("page", 0),
                chunk_id=p.get("chunk_id", 0),
                source_type=p.get("source_type", "text")
            )
            candidate_scores[chunk_key] = {
                "dense_score": float(hit.score),
                "bm25_score": 0.0,
                "chunk": chunk
            }

        # Local BM25 search
        for _, bm25_score, chunk in self._bm25_search(query, document_filter, pool_size):
            current = candidate_scores.setdefault(
                chunk.id,
                {"dense_score": 0.0, "bm25_score": 0.0, "chunk": chunk}
            )
            current["bm25_score"] = bm25_score

        # Combine scores
        max_bm25 = max((item["bm25_score"] for item in candidate_scores.values()), default=0.0)
        weighted_candidates: list[RetrievedChunk] = []
        for chunk_key, scores_by_type in candidate_scores.items():
            chunk = scores_by_type["chunk"]
            dense_score = scores_by_type["dense_score"]
            bm25_score = scores_by_type["bm25_score"]
            
            normalized_dense = max(0.0, min(dense_score, 1.0))
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
                    source_type=chunk.source_type
                )
            )

        ranked = sorted(
            weighted_candidates,
            key=lambda item: (item.score, item.bm25_score, item.dense_score),
            reverse=True
        )
        return ranked[:top_k]
