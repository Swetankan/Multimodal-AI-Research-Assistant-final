from __future__ import annotations

import json

from fastapi.testclient import TestClient

from main import create_app


class FakeVectorStore:
    def __init__(self) -> None:
        self.cleared = False
        self.documents_indexed = True
        self.count = 3

    def has_documents(self) -> bool:
        return self.documents_indexed

    def document_count(self) -> int:
        return self.count

    def describe(self) -> dict[str, object]:
        return {
            "storage_dir": "memory",
            "chunks_indexed": self.count,
            "persisted": False,
        }

    def clear(self) -> None:
        self.cleared = True
        self.documents_indexed = False
        self.count = 0


class FakePipeline:
    def __init__(self) -> None:
        self.vector_store = FakeVectorStore()
        self.ingested: list[tuple[str, int]] = []
        self.documents = [
            {
                "document_id": "doc-1",
                "filename": "paper.pdf",
                "uploaded_at": "2026-05-26T00:00:00+00:00",
                "chunk_count": 3,
                "source_type": "pdf",
            }
        ]

    def ingest_pdf(self, file_path: str, chunk_size: int = 700, filename: str | None = None) -> dict[str, object]:
        self.ingested.append((file_path, chunk_size))
        self.vector_store.documents_indexed = True
        self.vector_store.count = 5
        document = {
            "document_id": "doc-2",
            "filename": filename or "paper.pdf",
            "uploaded_at": "2026-05-26T00:01:00+00:00",
            "chunk_count": 5,
            "source_type": "pdf",
        }
        self.documents.append(document)
        return document

    def list_documents(self) -> list[dict[str, object]]:
        return self.documents

    def clear_documents(self) -> None:
        self.vector_store.clear()
        self.documents = []

    def delete_document(self, document_id: str) -> int:
        before = len(self.documents)
        self.documents = [
            document for document in self.documents if document["document_id"] != document_id
        ]
        return 1 if len(self.documents) != before else 0

    async def stream_chat(
        self,
        query: str,
        history: list[dict[str, str]],
        provider: str,
        model: str,
        top_k: int,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False,
    ):
        del history, provider, model, top_k, document_ids, dense_weight, bm25_weight, candidate_pool_size
        for payload in (
            {"type": "thinking"},
            {"type": "token", "token": f"Echo: {query}"},
            {
                "type": "sources",
                "sources": [
                    {
                        "id": "chunk-1",
                        "text": "alpha",
                        "score": 0.9,
                        "document_id": "doc-1",
                        "filename": "paper.pdf",
                    }
                ],
            },
            {"type": "done"},
        ):
            yield json.dumps(payload) + "\n"

    async def stream_compare(
        self,
        document_ids: list[str],
        provider: str,
        model: str,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False,
    ):
        del provider, model, dense_weight, bm25_weight, candidate_pool_size
        for payload in (
            {"type": "thinking"},
            {"type": "token", "token": f"Comparison for docs: {', '.join(document_ids)}"},
            {
                "type": "sources",
                "sources": [
                    {
                        "id": "chunk-1",
                        "text": "alpha",
                        "score": 0.9,
                        "document_id": document_ids[0],
                        "filename": "paper.pdf",
                    }
                ],
            },
            {"type": "done"},
        ):
            yield json.dumps(payload) + "\n"

    def retrieval_debug(
        self,
        query: str,
        top_k: int,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False,
    ) -> dict[str, object]:
        return {
            "query": query,
            "top_k": top_k,
            "document_ids": document_ids or [],
            "retrieval": {
                "dense_weight": dense_weight,
                "bm25_weight": bm25_weight,
                "candidate_pool_size": candidate_pool_size,
                "rerank": rerank,
            },
            "results": [{"id": "chunk-1", "text": "alpha", "score": 0.9}],
        }

    def evaluate_retrieval(
        self,
        query: str,
        expected_terms: list[str],
        top_k: int,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False,
    ) -> dict[str, object]:
        del dense_weight, bm25_weight, candidate_pool_size, rerank
        return {
            "query": query,
            "top_k": top_k,
            "document_ids": document_ids or [],
            "expected_terms": expected_terms,
            "matched_terms": expected_terms[:1],
            "term_recall": 1.0 if expected_terms else 0.0,
            "any_hit": bool(expected_terms),
            "results": [{"id": "chunk-1", "text": "alpha", "score": 0.9}],
        }

    async def generate_presentation(
        self,
        document_ids: list[str],
        provider: str,
        model: str,
        output_path: str | Path
    ) -> None:
        from pptx import Presentation
        prs = Presentation()
        prs.save(str(output_path))


def create_test_client() -> tuple[TestClient, FakePipeline]:
    pipeline = FakePipeline()
    app = create_app(pipeline)
    return TestClient(app), pipeline


def test_healthcheck_returns_vector_store_metadata() -> None:
    client, _ = create_test_client()

    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["documents_indexed"] is True
    assert body["vector_store"]["chunks_indexed"] == 3
    assert body["documents"][0]["document_id"] == "doc-1"


def test_upload_rejects_non_pdf_files() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/upload",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF uploads are supported"


def test_upload_rejects_invalid_magic_header_pdf() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/upload",
        files={"file": ("fake_paper.pdf", b"plain text with pdf extension", "application/pdf")},
    )

    assert response.status_code == 400
    assert "Invalid PDF file" in response.json()["detail"]


def test_upload_rejects_empty_pdf() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded PDF is empty"


def test_upload_rejects_oversized_pdf() -> None:
    client, _ = create_test_client()
    client.app.state.max_upload_bytes = 4

    response = client.post(
        "/upload",
        files={"file": ("large.pdf", b"%PDF-1.4 oversized", "application/pdf")},
    )

    assert response.status_code == 413
    assert "Maximum upload size" in response.json()["detail"]


def test_upload_rejects_invalid_chunk_size() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/upload",
        data={"chunk_size": "100"},
        files={"file": ("paper.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "chunk_size must be between 200 and 2000"


def test_upload_accepts_pdf_and_calls_pipeline() -> None:
    client, pipeline = create_test_client()

    response = client.post(
        "/upload",
        data={"chunk_size": "512"},
        files={"file": ("paper.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chunks_indexed"] == 5
    assert body["document_id"] == "doc-2"
    assert body["filename"] == "paper.pdf"
    assert pipeline.ingested
    assert pipeline.ingested[0][1] == 512


def test_reset_all_clears_vector_store() -> None:
    client, pipeline = create_test_client()

    response = client.post("/reset", json={"mode": "all"})

    assert response.status_code == 200
    assert pipeline.vector_store.cleared is True
    assert pipeline.documents == []
    assert response.json()["vector_store"]["chunks_indexed"] == 0


def test_reset_chat_keeps_documents() -> None:
    client, pipeline = create_test_client()

    response = client.post("/reset", json={"mode": "chat"})

    assert response.status_code == 200
    assert pipeline.vector_store.cleared is False
    assert response.json()["documents"][0]["document_id"] == "doc-1"


def test_reset_document_deletes_one_document() -> None:
    client, pipeline = create_test_client()

    response = client.post("/reset", json={"mode": "document", "document_id": "doc-1"})

    assert response.status_code == 200
    assert response.json()["document_id"] == "doc-1"
    assert pipeline.documents == []


def test_documents_endpoint_returns_registry() -> None:
    client, _ = create_test_client()

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json()["documents"][0]["filename"] == "paper.pdf"


def test_chat_streams_expected_events() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/chat",
        json={
            "query": "summarize this",
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
            "top_k": 4,
            "document_ids": ["doc-1"],
            "dense_weight": 0.5,
            "bm25_weight": 0.5,
            "candidate_pool_size": 16,
            "history": [],
        },
    )

    assert response.status_code == 200
    lines = [json.loads(line) for line in response.text.strip().splitlines()]
    assert lines[0]["type"] == "thinking"
    assert lines[1]["type"] == "token"
    assert lines[-1]["type"] == "done"


def test_retrieval_debug_accepts_hybrid_settings() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/retrieval/debug",
        json={
            "query": "benchmark",
            "top_k": 4,
            "dense_weight": 0.4,
            "bm25_weight": 0.6,
            "candidate_pool_size": 20,
        },
    )

    assert response.status_code == 200
    retrieval = response.json()["retrieval"]
    assert retrieval["dense_weight"] == 0.4
    assert retrieval["bm25_weight"] == 0.6
    assert retrieval["candidate_pool_size"] == 20


def test_retrieval_evaluate_returns_metrics() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/retrieval/evaluate",
        json={
            "query": "key contributions",
            "expected_terms": ["benchmark", "ablation"],
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "key contributions"
    assert body["term_recall"] == 1.0
    assert body["any_hit"] is True


def test_compare_streams_expected_events() -> None:
    client, pipeline = create_test_client()
    pipeline.documents.append({
        "document_id": "doc-2",
        "filename": "another_paper.pdf",
        "uploaded_at": "2026-05-26T00:01:00+00:00",
        "chunk_count": 5,
        "source_type": "pdf",
    })

    response = client.post(
        "/compare",
        json={
            "document_ids": ["doc-1", "doc-2"],
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
            "dense_weight": 0.72,
            "bm25_weight": 0.28,
            "candidate_pool_size": 24,
        }
    )

    assert response.status_code == 200
    lines = [json.loads(line) for line in response.text.strip().splitlines()]
    assert lines[0]["type"] == "thinking"
    assert lines[1]["type"] == "token"
    assert "Comparison for docs:" in lines[1]["token"]
    assert lines[-1]["type"] == "done"


def test_compare_validates_document_ids() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/compare",
        json={
            "document_ids": ["doc-1", "doc-3"],
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
        }
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_generate_ppt_returns_file() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/generate-ppt",
        json={
            "document_ids": ["doc-1"],
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
        }
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert "paper_summary.pptx" in response.headers["content-disposition"]
    assert len(response.content) > 0


def test_generate_ppt_validates_document_ids() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/generate-ppt",
        json={
            "document_ids": ["doc-3"],
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
        }
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_session_isolation_partitions_documents() -> None:
    from pathlib import Path
    from main import create_app
    from fastapi.testclient import TestClient
    import shutil

    app = create_app()
    client = TestClient(app)

    base_storage = Path("storage")
    shutil.rmtree(base_storage / "session-a", ignore_errors=True)
    shutil.rmtree(base_storage / "session-b", ignore_errors=True)

    try:
        resp_a = client.get("/documents", headers={"X-Session-ID": "session-a"})
        resp_b = client.get("/documents", headers={"X-Session-ID": "session-b"})
        assert resp_a.json()["documents"] == []
        assert resp_b.json()["documents"] == []

        pdf_path = Path("../77_2312res902_Swetankan.pdf")
        if not pdf_path.exists():
            # Fallback if tests are run from a different directory
            pdf_path = Path("77_2312res902_Swetankan.pdf")
            
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        resp_upload = client.post(
            "/upload",
            headers={"X-Session-ID": "session-a"},
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")}
        )
        assert resp_upload.status_code == 200

        resp_a = client.get("/documents", headers={"X-Session-ID": "session-a"})
        assert len(resp_a.json()["documents"]) == 1

        resp_b = client.get("/documents", headers={"X-Session-ID": "session-b"})
        assert resp_b.json()["documents"] == []

    finally:
        shutil.rmtree(base_storage / "session-a", ignore_errors=True)
        shutil.rmtree(base_storage / "session-b", ignore_errors=True)


def test_chat_accepts_rerank_parameter() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/chat",
        json={
            "query": "summarize this",
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
            "top_k": 4,
            "document_ids": ["doc-1"],
            "dense_weight": 0.5,
            "bm25_weight": 0.5,
            "candidate_pool_size": 16,
            "rerank": True,
            "history": [],
        },
    )

    assert response.status_code == 200


def test_retrieval_debug_accepts_rerank_parameter() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/retrieval/debug",
        json={
            "query": "benchmark",
            "top_k": 4,
            "document_ids": ["doc-1"],
            "dense_weight": 0.5,
            "bm25_weight": 0.5,
            "candidate_pool_size": 16,
            "rerank": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["retrieval"]["rerank"] is True


def test_qdrant_vector_store_instantiation(tmp_path) -> None:
    import os
    os.environ["VECTOR_DB_PROVIDER"] = "qdrant"
    try:
        from qdrant_store import QdrantVectorStore
        store = QdrantVectorStore(
            embedding_model="sentence-transformers/paraphrase-MiniLM-L3-v2",
            storage_dir=tmp_path
        )
        desc = store.describe()
        assert desc["provider"] == "qdrant"
        assert desc["is_local"] is True
        assert desc["chunks_indexed"] == 0
    finally:
        os.environ.pop("VECTOR_DB_PROVIDER", None)
