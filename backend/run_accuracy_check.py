from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from rag_pipeline import ResearchAssistantPipeline


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Evaluation cases file must be a JSON array.")
    return payload


def evaluate_cases(
    pipeline: Any,
    cases: list[dict[str, Any]],
    default_top_k: int = 4,
    retrieval_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evaluations: list[dict[str, Any]] = []
    settings = retrieval_settings or {}

    for index, case in enumerate(cases, start=1):
        query = str(case.get("query", "")).strip()
        if not query:
            raise ValueError(f"Case {index} is missing a query.")

        expected_terms = [
            str(term).strip()
            for term in case.get("expected_terms", [])
            if str(term).strip()
        ]
        top_k = int(case.get("top_k", default_top_k))
        result = pipeline.evaluate_retrieval(
            query=query,
            expected_terms=expected_terms,
            top_k=top_k,
            document_ids=case.get("document_ids", []),
            dense_weight=float(case.get("dense_weight", settings.get("dense_weight", 0.72))),
            bm25_weight=float(case.get("bm25_weight", settings.get("bm25_weight", 0.28))),
            candidate_pool_size=int(case.get("candidate_pool_size", settings.get("candidate_pool_size", 24))),
        )
        ranking_metrics = compute_retrieval_metrics(
            results=result.get("results", []),
            expected_terms=expected_terms,
            expected_document_ids=case.get("expected_document_ids", []),
            expected_chunk_ids=case.get("expected_chunk_ids", []),
            top_k=top_k,
        )
        evaluations.append(
            {
                "name": case.get("name") or f"case-{index}",
                "query": query,
                "top_k": top_k,
                **result,
                **ranking_metrics,
            }
        )

    case_count = len(evaluations)
    avg_term_recall = round(
        sum(float(item["term_recall"]) for item in evaluations) / case_count,
        4,
    ) if evaluations else 0.0
    hit_rate = round(
        sum(1 for item in evaluations if item["any_hit"]) / case_count,
        4,
    ) if evaluations else 0.0
    avg_precision = _average(evaluations, "precision_at_k")
    avg_recall = _average(evaluations, "recall_at_k")
    avg_mrr = _average(evaluations, "mrr")
    avg_ndcg = _average(evaluations, "ndcg_at_k")
    avg_citation_coverage = _average(evaluations, "citation_coverage")

    return {
        "summary": {
            "case_count": case_count,
            "avg_term_recall": avg_term_recall,
            "hit_rate": hit_rate,
            "avg_precision_at_k": avg_precision,
            "avg_recall_at_k": avg_recall,
            "avg_mrr": avg_mrr,
            "avg_ndcg_at_k": avg_ndcg,
            "avg_citation_coverage": avg_citation_coverage,
        },
        "retrieval_settings": settings,
        "cases": evaluations,
    }


def compute_retrieval_metrics(
    results: Any,
    expected_terms: list[str],
    expected_document_ids: list[str],
    expected_chunk_ids: list[str],
    top_k: int,
) -> dict[str, float | int]:
    result_items = results if isinstance(results, list) else []
    expected_terms_normalized = [term.lower() for term in expected_terms]
    expected_doc_set = {str(item) for item in expected_document_ids if str(item).strip()}
    expected_chunk_set = {str(item) for item in expected_chunk_ids if str(item).strip()}
    relevance: list[int] = []
    matched_terms: set[str] = set()
    cited_documents: set[str] = set()

    for item in result_items[:top_k]:
        text = str(item.get("text", "")).lower() if isinstance(item, dict) else ""
        document_id = str(item.get("document_id", "")) if isinstance(item, dict) else ""
        chunk_id = str(item.get("id", "")) if isinstance(item, dict) else ""
        if document_id:
            cited_documents.add(document_id)

        term_matches = {term for term in expected_terms_normalized if term in text}
        matched_terms.update(term_matches)
        is_relevant = bool(term_matches)
        if expected_doc_set:
            is_relevant = is_relevant or document_id in expected_doc_set
        if expected_chunk_set:
            is_relevant = is_relevant or chunk_id in expected_chunk_set
        relevance.append(1 if is_relevant else 0)

    relevant_count = sum(relevance)
    precision_at_k = relevant_count / top_k if top_k else 0.0
    recall_denominator = max(len(expected_terms_normalized), len(expected_doc_set), len(expected_chunk_set), 1)
    recall_numerator = max(len(matched_terms), len(cited_documents & expected_doc_set), relevant_count if expected_chunk_set else 0)
    recall_at_k = min(recall_numerator / recall_denominator, 1.0)
    first_relevant_rank = next((index + 1 for index, value in enumerate(relevance) if value), 0)
    mrr = 1 / first_relevant_rank if first_relevant_rank else 0.0
    dcg = sum(value / math.log2(index + 2) for index, value in enumerate(relevance))
    ideal_relevance = sorted(relevance, reverse=True)
    idcg = sum(value / math.log2(index + 2) for index, value in enumerate(ideal_relevance))
    ndcg = dcg / idcg if idcg else 0.0
    citation_coverage = (
        len(cited_documents & expected_doc_set) / len(expected_doc_set)
        if expected_doc_set
        else (1.0 if result_items else 0.0)
    )

    return {
        "precision_at_k": round(precision_at_k, 4),
        "recall_at_k": round(recall_at_k, 4),
        "mrr": round(mrr, 4),
        "ndcg_at_k": round(ndcg, 4),
        "citation_coverage": round(citation_coverage, 4),
        "first_relevant_rank": first_relevant_rank,
    }


def _average(items: list[dict[str, Any]], key: str) -> float:
    if not items:
        return 0.0
    return round(sum(float(item.get(key, 0.0)) for item in items) / len(items), 4)


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Retrieval Evaluation Report",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")

    lines.extend([
        "",
        "## Cases",
        "",
        "| Case | Precision@k | Recall@k | MRR | nDCG@k | Citation Coverage | Term Recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for case in report["cases"]:
        lines.append(
            "| {name} | {precision_at_k} | {recall_at_k} | {mrr} | {ndcg_at_k} | {citation_coverage} | {term_recall} |".format(
                **case
            )
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run retrieval accuracy checks against the current persisted vector store."
    )
    parser.add_argument(
        "--cases",
        default="eval_cases.sample.json",
        help="Path to a JSON file containing retrieval evaluation cases.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Default top-k value for cases that do not specify one.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write the JSON report.",
    )
    parser.add_argument(
        "--markdown-output",
        default="",
        help="Optional path to write a Markdown summary report.",
    )
    parser.add_argument("--dense-weight", type=float, default=0.72)
    parser.add_argument("--bm25-weight", type=float, default=0.28)
    parser.add_argument("--candidate-pool-size", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases_path = Path(args.cases)
    if not cases_path.is_absolute():
        cases_path = Path(__file__).with_name(args.cases)

    if not cases_path.exists():
        raise SystemExit(f"Cases file not found: {cases_path}")

    pipeline = ResearchAssistantPipeline()
    if not pipeline.vector_store.has_documents():
        raise SystemExit(
            "No indexed PDF context found. Upload a PDF first, then run the accuracy check."
        )

    report = evaluate_cases(
        pipeline=pipeline,
        cases=load_cases(cases_path),
        default_top_k=args.top_k,
        retrieval_settings={
            "dense_weight": args.dense_weight,
            "bm25_weight": args.bm25_weight,
            "candidate_pool_size": args.candidate_pool_size,
            "rerank": False,
        },
    )

    output = json.dumps(report, indent=2, ensure_ascii=True)
    print(output)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.write_text(output, encoding="utf-8")

    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        if not markdown_path.is_absolute():
            markdown_path = Path.cwd() / markdown_path
        markdown_path.write_text(render_markdown_report(report), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
