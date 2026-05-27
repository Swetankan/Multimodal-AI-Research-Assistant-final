from __future__ import annotations

from vector_store import FaissVectorStore, RetrievedChunk


def test_bm25_search_prioritizes_exact_term_matches() -> None:
    store = object.__new__(FaissVectorStore)
    store.chunks = [
        RetrievedChunk(id="chunk-1", text="benchmark neural network overview", score=0.0),
        RetrievedChunk(id="chunk-2", text="ablation benchmark benchmark dataset", score=0.0),
    ]

    results = store._bm25_search("benchmark ablation", document_filter=set(), pool_size=2)

    assert results[0][0] == 1
    assert results[0][1] > results[-1][1]


def test_bm25_search_respects_document_filter() -> None:
    store = object.__new__(FaissVectorStore)
    store.chunks = [
        RetrievedChunk(id="chunk-1", text="benchmark ablation", score=0.0, document_id="doc-1"),
        RetrievedChunk(id="chunk-2", text="benchmark ablation benchmark", score=0.0, document_id="doc-2"),
    ]

    results = store._bm25_search("benchmark", document_filter={"doc-1"}, pool_size=5)

    assert len(results) == 1
    assert results[0][0] == 0
