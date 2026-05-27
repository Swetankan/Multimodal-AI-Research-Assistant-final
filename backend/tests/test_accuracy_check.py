from __future__ import annotations

from run_accuracy_check import compute_retrieval_metrics, evaluate_cases, render_markdown_report


class StubPipeline:
    def evaluate_retrieval(
        self,
        query: str,
        expected_terms: list[str],
        top_k: int,
        **kwargs: object,
    ) -> dict[str, object]:
        del top_k, kwargs
        matched_terms = [term for term in expected_terms if term in query.lower()]
        recall = len(matched_terms) / len(expected_terms) if expected_terms else 0.0
        return {
            "query": query,
            "expected_terms": expected_terms,
            "matched_terms": matched_terms,
            "term_recall": round(recall, 4),
            "any_hit": bool(matched_terms),
            "results": [
                {
                    "id": "chunk-1",
                    "text": query,
                    "document_id": "doc-1",
                    "filename": "paper.pdf",
                }
            ],
        }


def test_evaluate_cases_aggregates_summary() -> None:
    pipeline = StubPipeline()
    cases = [
        {"name": "one", "query": "benchmark ablation", "expected_terms": ["benchmark", "ablation"]},
        {"name": "two", "query": "only benchmark", "expected_terms": ["benchmark", "theorem"]},
    ]

    report = evaluate_cases(pipeline, cases, default_top_k=4)

    assert report["summary"]["case_count"] == 2
    assert report["summary"]["avg_term_recall"] == 0.75
    assert report["summary"]["hit_rate"] == 1.0
    assert report["summary"]["avg_precision_at_k"] > 0
    assert report["summary"]["avg_mrr"] == 1.0
    assert report["cases"][0]["name"] == "one"


def test_compute_retrieval_metrics_uses_terms_and_citations() -> None:
    metrics = compute_retrieval_metrics(
        results=[
            {"id": "chunk-1", "text": "benchmark ablation", "document_id": "doc-1"},
            {"id": "chunk-2", "text": "unrelated", "document_id": "doc-2"},
        ],
        expected_terms=["benchmark", "ablation"],
        expected_document_ids=["doc-1"],
        expected_chunk_ids=[],
        top_k=2,
    )

    assert metrics["precision_at_k"] == 0.5
    assert metrics["recall_at_k"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["citation_coverage"] == 1.0


def test_render_markdown_report_outputs_summary_table() -> None:
    report = evaluate_cases(
        StubPipeline(),
        [{"name": "one", "query": "benchmark", "expected_terms": ["benchmark"]}],
    )

    markdown = render_markdown_report(report)

    assert "# Retrieval Evaluation Report" in markdown
    assert "| case_count | 1 |" in markdown
    assert "| one |" in markdown
