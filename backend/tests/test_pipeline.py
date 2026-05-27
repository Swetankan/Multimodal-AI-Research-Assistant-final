from __future__ import annotations

from rag_pipeline import ResearchAssistantPipeline
from vector_store import RetrievedChunk


class StubVectorStore:
    def __init__(self, results: list[RetrievedChunk] | None = None) -> None:
        self.results = results or []

    def search(
        self,
        query: str,
        top_k: int = 4,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
    ) -> list[RetrievedChunk]:
        del query, top_k, document_ids, dense_weight, bm25_weight, candidate_pool_size
        return self.results

    def describe(self) -> dict[str, object]:
        return {"chunks_indexed": len(self.results), "persisted": False}

    def document_count(self) -> int:
        return len(self.results)

    def has_documents(self) -> bool:
        return bool(self.results)


def build_pipeline(results: list[RetrievedChunk]) -> ResearchAssistantPipeline:
    pipeline = object.__new__(ResearchAssistantPipeline)
    pipeline.vector_store = StubVectorStore(results)
    pipeline._trace_retrieval = lambda **_: None
    pipeline._trace_retrieval_evaluation = lambda **_: None
    pipeline._trace_prompt = lambda **_: None
    pipeline._trace_identity = lambda **_: None
    pipeline._trace_generation = lambda **_: None
    pipeline._trace_generation_error = lambda **_: None
    return pipeline


def test_evaluate_retrieval_matches_expected_terms() -> None:
    pipeline = build_pipeline(
        [
            RetrievedChunk(
                id="chunk-1",
                text="This paper reports a benchmark improvement and an ablation study.",
                score=0.91,
                dense_score=0.83,
                lexical_score=0.74,
            )
        ]
    )

    evaluation = pipeline.evaluate_retrieval(
        query="What are the contributions?",
        expected_terms=["benchmark", "ablation", "theorem"],
        top_k=3,
    )

    assert evaluation["matched_terms"] == ["benchmark", "ablation"]
    assert evaluation["term_recall"] == 0.6667
    assert evaluation["any_hit"] is True


def test_identity_response_includes_developer_attribution() -> None:
    assert ResearchAssistantPipeline._is_identity_query("who created you?") is True
    response = ResearchAssistantPipeline._identity_response("who created you with OpenAI?")
    assert "Swetankan Kumar Sinha and his team" in response
    assert "OpenAI" in response
