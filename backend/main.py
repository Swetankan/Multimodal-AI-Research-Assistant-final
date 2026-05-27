from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

import re
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from rag_pipeline import ResearchAssistantPipeline

load_dotenv(Path(__file__).with_name(".env"))

DEFAULT_MAX_UPLOAD_BYTES = 15 * 1024 * 1024

frontend_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
extra_origins = [
    item.strip()
    for item in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if item.strip()
]
frontend_origins.extend(extra_origins)

allowed_origin_regex = (
    r"^https?://("
    r"(localhost|127\.0\.0\.1)"
    r"|(192\.168\.\d+\.\d+)"
    r"|(10\.\d+\.\d+\.\d+)"
    r"|(172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)"
    r"|([a-zA-Z0-9-]+\.)*vercel\.app"
    r")(:\d+)?$"
)


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    provider: Literal["openrouter", "ollama"] = "openrouter"
    model: str = "openai/gpt-4o-mini"
    top_k: int = Field(default=4, ge=1, le=12)
    document_ids: list[str] = Field(default_factory=list)
    dense_weight: float = Field(default=0.72, ge=0, le=1)
    bm25_weight: float = Field(default=0.28, ge=0, le=1)
    candidate_pool_size: int = Field(default=24, ge=4, le=100)
    rerank: bool = False
    history: list[HistoryMessage] = Field(default_factory=list)


class RetrievalDebugRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)
    document_ids: list[str] = Field(default_factory=list)
    dense_weight: float = Field(default=0.72, ge=0, le=1)
    bm25_weight: float = Field(default=0.28, ge=0, le=1)
    candidate_pool_size: int = Field(default=24, ge=4, le=100)
    rerank: bool = False


class RetrievalEvaluationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    expected_terms: list[str] = Field(default_factory=list)
    top_k: int = Field(default=4, ge=1, le=20)
    document_ids: list[str] = Field(default_factory=list)
    dense_weight: float = Field(default=0.72, ge=0, le=1)
    bm25_weight: float = Field(default=0.28, ge=0, le=1)
    candidate_pool_size: int = Field(default=24, ge=4, le=100)
    rerank: bool = False


class ResetRequest(BaseModel):
    mode: Literal["chat", "document", "all"] = "all"
    document_id: str | None = None


class CompareRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=2)
    provider: Literal["openrouter", "ollama"] = "openrouter"
    model: str = "openai/gpt-4o-mini"
    dense_weight: float = Field(default=0.72, ge=0, le=1)
    bm25_weight: float = Field(default=0.28, ge=0, le=1)
    candidate_pool_size: int = Field(default=24, ge=4, le=100)
    rerank: bool = False


class GeneratePptRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=1)
    provider: Literal["openrouter", "ollama"] = "openrouter"
    model: str = "openai/gpt-4o-mini"


def create_app(pipeline_override: ResearchAssistantPipeline | None = None) -> FastAPI:
    app = FastAPI(title="Multimodal AI Research Assistant API")
    app.state.pipeline_override = pipeline_override
    app.state.pipelines = {}
    app.state.max_upload_bytes = int(
        os.getenv("MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES))
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,
        allow_origin_regex=allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_pipeline(request: Request) -> ResearchAssistantPipeline:
        if request.app.state.pipeline_override is not None:
            return request.app.state.pipeline_override

        x_session_id = request.headers.get("X-Session-ID")
        session_key = x_session_id or "default-session"
        session_key = re.sub(r"[^a-zA-Z0-9_-]", "", session_key)
        if not session_key:
            session_key = "default-session"

        pipelines = request.app.state.pipelines
        if session_key not in pipelines:
            base_dir = os.getenv("VECTOR_STORE_DIR", str(Path(__file__).parent / "storage"))
            session_dir = Path(base_dir) / session_key
            pipelines[session_key] = ResearchAssistantPipeline(storage_dir=session_dir)
        return pipelines[session_key]

    @app.get("/")
    async def healthcheck(request: Request) -> JSONResponse:
        pipeline = get_pipeline(request)
        return JSONResponse(
            {
                "status": "ok",
                "documents_indexed": pipeline.vector_store.has_documents(),
                "chunks_indexed": pipeline.vector_store.document_count(),
                "documents": pipeline.list_documents(),
                "vector_store": pipeline.vector_store.describe(),
                "allowed_origins": frontend_origins,
                "allowed_origin_regex": allowed_origin_regex,
            }
        )

    @app.post("/upload")
    async def upload_pdf(
        request: Request,
        file: UploadFile = File(...),
        chunk_size: int = Form(default=700)
    ) -> JSONResponse:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Missing file name")

        if Path(file.filename).suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

        if chunk_size < 200 or chunk_size > 2000:
            raise HTTPException(status_code=400, detail="chunk_size must be between 200 and 2000")

        pipeline = get_pipeline(request)
        temp_path: str | None = None
        max_upload_bytes = request.app.state.max_upload_bytes
        bytes_written = 0
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_path = temp_file.name
                while chunk := await file.read(1024 * 1024):
                    if bytes_written == 0 and not chunk.startswith(b"%PDF-"):
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid PDF file. The uploaded file is not a valid PDF document."
                        )
                    bytes_written += len(chunk)
                    if bytes_written > max_upload_bytes:
                        limit_mb = max_upload_bytes / (1024 * 1024)
                        raise HTTPException(
                            status_code=413,
                            detail=f"PDF is too large. Maximum upload size is {limit_mb:.0f} MB."
                        )
                    temp_file.write(chunk)

            if bytes_written == 0:
                raise HTTPException(status_code=400, detail="Uploaded PDF is empty")

            document = pipeline.ingest_pdf(
                temp_path,
                chunk_size=chunk_size,
                filename=file.filename
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            await file.close()
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

        return JSONResponse(
            {
                "filename": file.filename,
                "document_id": document["document_id"],
                "chunks_indexed": document["chunk_count"],
                "document": document,
                "documents": pipeline.list_documents(),
                "message": f"PDF uploaded: {file.filename}",
                "vector_store": pipeline.vector_store.describe()
            }
        )

    @app.get("/documents")
    async def list_documents(request: Request) -> JSONResponse:
        pipeline = get_pipeline(request)
        return JSONResponse({"documents": pipeline.list_documents()})

    @app.post("/reset")
    async def reset_memory(request: Request, payload: ResetRequest | None = None) -> JSONResponse:
        pipeline = get_pipeline(request)
        reset_request = payload or ResetRequest()

        if reset_request.mode == "chat":
            return JSONResponse(
                {
                    "message": "Chat memory cleared.",
                    "documents": pipeline.list_documents(),
                    "vector_store": pipeline.vector_store.describe()
                }
            )

        if reset_request.mode == "document":
            if not reset_request.document_id:
                raise HTTPException(status_code=400, detail="document_id is required for document reset")
            removed_count = pipeline.delete_document(reset_request.document_id)
            if removed_count == 0:
                raise HTTPException(status_code=404, detail="Document not found")
            return JSONResponse(
                {
                    "message": "Document deleted.",
                    "document_id": reset_request.document_id,
                    "documents": pipeline.list_documents(),
                    "vector_store": pipeline.vector_store.describe()
                }
            )

        pipeline.clear_documents()
        return JSONResponse(
            {
                "message": "Chat memory and indexed PDF context cleared.",
                "documents": pipeline.list_documents(),
                "vector_store": pipeline.vector_store.describe()
            }
        )

    @app.post("/chat")
    async def chat(request: Request, payload: ChatRequest) -> StreamingResponse:
        pipeline = get_pipeline(request)
        history = [
            message.model_dump() if hasattr(message, "model_dump") else message.dict()
            for message in payload.history
        ]
        stream = pipeline.stream_chat(
            query=payload.query,
            history=history,
            provider=payload.provider,
            model=payload.model,
            top_k=payload.top_k,
            document_ids=payload.document_ids,
            dense_weight=payload.dense_weight,
            bm25_weight=payload.bm25_weight,
            candidate_pool_size=payload.candidate_pool_size,
            rerank=payload.rerank,
        )
        return StreamingResponse(stream, media_type="application/x-ndjson")

    @app.post("/compare")
    async def compare(request: Request, payload: CompareRequest) -> StreamingResponse:
        pipeline = get_pipeline(request)
        indexed_docs = {doc["document_id"] for doc in pipeline.list_documents()}
        for doc_id in payload.document_ids:
            if doc_id not in indexed_docs:
                raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found")

        stream = pipeline.stream_compare(
            document_ids=payload.document_ids,
            provider=payload.provider,
            model=payload.model,
            dense_weight=payload.dense_weight,
            bm25_weight=payload.bm25_weight,
            candidate_pool_size=payload.candidate_pool_size,
            rerank=payload.rerank,
        )
        return StreamingResponse(stream, media_type="application/x-ndjson")

    @app.post("/generate-ppt")
    async def generate_ppt(request: Request, payload: GeneratePptRequest) -> FileResponse:
        pipeline = get_pipeline(request)
        indexed_docs = {doc["document_id"] for doc in pipeline.list_documents()}
        for doc_id in payload.document_ids:
            if doc_id not in indexed_docs:
                raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found")

        from fastapi import BackgroundTasks

        temp_pptx = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
        temp_pptx_path = Path(temp_pptx.name)
        temp_pptx.close()

        def cleanup_file(path: Path):
            path.unlink(missing_ok=True)

        bg_tasks = BackgroundTasks()
        bg_tasks.add_task(cleanup_file, temp_pptx_path)

        try:
            await pipeline.generate_presentation(
                document_ids=payload.document_ids,
                provider=payload.provider,
                model=payload.model,
                output_path=temp_pptx_path
            )
        except Exception as exc:
            temp_pptx_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=str(exc))

        filename = "presentation.pptx"
        if len(payload.document_ids) == 1:
            doc = next(d for d in pipeline.list_documents() if d["document_id"] == payload.document_ids[0])
            name = Path(doc["filename"]).stem
            filename = f"{name}_summary.pptx"

        return FileResponse(
            path=str(temp_pptx_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            background=bg_tasks
        )

    @app.post("/retrieval/debug")
    async def retrieval_debug(request: Request, payload: RetrievalDebugRequest) -> JSONResponse:
        pipeline = get_pipeline(request)
        return JSONResponse(
            pipeline.retrieval_debug(
                query=payload.query,
                top_k=payload.top_k,
                document_ids=payload.document_ids,
                dense_weight=payload.dense_weight,
                bm25_weight=payload.bm25_weight,
                candidate_pool_size=payload.candidate_pool_size,
                rerank=payload.rerank,
            )
        )

    @app.post("/retrieval/evaluate")
    async def retrieval_evaluate(
        request: Request,
        payload: RetrievalEvaluationRequest
    ) -> JSONResponse:
        pipeline = get_pipeline(request)
        return JSONResponse(
            pipeline.evaluate_retrieval(
                query=payload.query,
                expected_terms=payload.expected_terms,
                top_k=payload.top_k,
                document_ids=payload.document_ids,
                dense_weight=payload.dense_weight,
                bm25_weight=payload.bm25_weight,
                candidate_pool_size=payload.candidate_pool_size,
                rerank=payload.rerank,
            )
        )

    return app


app = create_app()
