from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from langsmith import traceable

from pdf_utils import extract_pdf_with_diagnostics
from vector_store import FaissVectorStore, RetrievedChunk
from ppt_utils import generate_pptx_deck

_RERANKER_CACHE = {}

def get_reranker(model_name: str):
    if model_name not in _RERANKER_CACHE:
        from sentence_transformers import CrossEncoder
        _RERANKER_CACHE[model_name] = CrossEncoder(model_name)
    return _RERANKER_CACHE[model_name]

load_dotenv(Path(__file__).with_name(".env"))


class ResearchAssistantPipeline:
    def __init__(self, storage_dir: str | Path | None = None) -> None:
        embedding_model = os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        if storage_dir is None:
            storage_dir = os.getenv(
                "VECTOR_STORE_DIR",
                str(Path(__file__).with_name("storage"))
            )
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1"
        )
        self.openrouter_default_model = os.getenv(
            "OPENROUTER_MODEL",
            "openai/gpt-4o-mini"
        )
        self.openrouter_site_url = os.getenv(
            "OPENROUTER_SITE_URL",
            "http://localhost:3000"
        )
        self.openrouter_app_name = os.getenv(
            "OPENROUTER_APP_NAME",
            "Multimodal AI Research Assistant"
        )
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_timeout_seconds = float(os.getenv("MODEL_TIMEOUT_SECONDS", "45"))
        
        db_provider = os.getenv("VECTOR_DB_PROVIDER", "faiss").lower()
        if db_provider == "qdrant":
            from qdrant_store import QdrantVectorStore
            self.vector_store = QdrantVectorStore(
                embedding_model=embedding_model,
                storage_dir=storage_dir
            )
        else:
            self.vector_store = FaissVectorStore(
                embedding_model=embedding_model,
                storage_dir=storage_dir
            )
        self.documents = self._documents_from_chunks()

    def ingest_pdf(
        self,
        file_path: str,
        chunk_size: int = 700,
        filename: str | None = None
    ) -> dict[str, Any]:
        extraction = extract_pdf_with_diagnostics(file_path, chunk_size=chunk_size)
        chunks = extraction.chunks
        document_id = f"doc-{uuid4().hex[:12]}"
        display_name = filename or Path(file_path).name
        indexed = self.vector_store.add_texts(
            [chunk.text for chunk in chunks],
            document_id=document_id,
            filename=display_name,
            pages=[chunk.page for chunk in chunks],
            source_types=[chunk.source_type for chunk in chunks],
        )
        document = {
            "document_id": document_id,
            "filename": display_name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "chunk_count": indexed,
            "source_type": "pdf",
            "extraction": extraction.diagnostics,
        }
        self.documents[document_id] = document
        self._trace_pdf_ingestion(
            file_path=file_path,
            chunk_size=chunk_size,
            chunks_indexed=indexed,
            vector_store=self.vector_store.describe()
        )
        return document

    def list_documents(self) -> list[dict[str, Any]]:
        return sorted(
            self.documents.values(),
            key=lambda item: str(item.get("uploaded_at", "")),
            reverse=True
        )

    def clear_documents(self) -> None:
        self.vector_store.clear()
        self.documents = {}

    def delete_document(self, document_id: str) -> int:
        removed_count = self.vector_store.delete_document(document_id)
        if removed_count:
            self.documents.pop(document_id, None)
        return removed_count

    def rerank_chunks(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        reranker_model_name = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        reranker = get_reranker(reranker_model_name)
        pairs = [[query, chunk.text] for chunk in chunks]
        scores = reranker.predict(pairs)
        
        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)
            chunk.score = float(score)
            
        ranked = sorted(chunks, key=lambda item: item.rerank_score, reverse=True)
        return ranked[:top_k]

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False
    ) -> list[RetrievedChunk]:
        if rerank:
            pool_size = candidate_pool_size or 24
            results = self.vector_store.search(
                query,
                top_k=pool_size,
                document_ids=document_ids,
                dense_weight=dense_weight,
                bm25_weight=bm25_weight,
                candidate_pool_size=pool_size,
            )
            results = self.rerank_chunks(query, results, top_k)
        else:
            results = self.vector_store.search(
                query,
                top_k=top_k,
                document_ids=document_ids,
                dense_weight=dense_weight,
                bm25_weight=bm25_weight,
                candidate_pool_size=candidate_pool_size,
            )
        self._trace_retrieval(query=query, top_k=top_k, results=results)
        return results

    def retrieval_debug(
        self,
        query: str,
        top_k: int = 4,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False
    ) -> dict[str, Any]:
        results = self.retrieve(
            query=query,
            top_k=top_k,
            document_ids=document_ids,
            dense_weight=dense_weight,
            bm25_weight=bm25_weight,
            candidate_pool_size=candidate_pool_size,
            rerank=rerank
        )
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
            "documents_indexed": self.vector_store.document_count(),
            "documents": self.list_documents(),
            "vector_store": self.vector_store.describe(),
            "results": [self._chunk_to_payload(chunk) for chunk in results]
        }

    def evaluate_retrieval(
        self,
        query: str,
        expected_terms: list[str],
        top_k: int = 4,
        document_ids: list[str] | None = None,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False
    ) -> dict[str, Any]:
        results = self.retrieve(
            query=query,
            top_k=top_k,
            document_ids=document_ids,
            dense_weight=dense_weight,
            bm25_weight=bm25_weight,
            candidate_pool_size=candidate_pool_size,
            rerank=rerank
        )
        normalized_terms = [term.strip().lower() for term in expected_terms if term.strip()]

        if not normalized_terms:
            return {
                "query": query,
                "top_k": top_k,
                "document_ids": document_ids or [],
                "expected_terms": [],
                "matched_terms": [],
                "term_recall": 0.0,
                "any_hit": False,
                "results": [self._chunk_to_payload(chunk) for chunk in results]
            }

        corpus = "\n\n".join(chunk.text.lower() for chunk in results)
        matched_terms = [term for term in normalized_terms if term in corpus]
        term_recall = len(matched_terms) / len(normalized_terms)
        evaluation = {
            "query": query,
            "top_k": top_k,
            "document_ids": document_ids or [],
            "expected_terms": normalized_terms,
            "matched_terms": matched_terms,
            "term_recall": round(term_recall, 4),
            "any_hit": bool(matched_terms),
            "results": [self._chunk_to_payload(chunk) for chunk in results]
        }
        self._trace_retrieval_evaluation(**evaluation)
        return evaluation

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
        rerank: bool = False
    ):
        yield self._event({"type": "thinking"})

        if self._is_identity_query(query):
            identity_text = self._identity_response(query)
            self._trace_identity(query=query, response=identity_text)
            async for token in self._stream_text(identity_text):
                yield self._event({"type": "token", "token": token})
            yield self._event({"type": "sources", "sources": []})
            yield self._event({"type": "done"})
            return

        contexts = (
            self.retrieve(
                query,
                top_k=top_k,
                document_ids=document_ids,
                dense_weight=dense_weight,
                bm25_weight=bm25_weight,
                candidate_pool_size=candidate_pool_size,
                rerank=rerank
            )
            if self.vector_store.has_documents()
            else []
        )
        messages = self._build_messages(query=query, history=history, contexts=contexts)
        collected_tokens: list[str] = []

        try:
            if provider == "ollama":
                async for token in self._stream_from_ollama(model=model, messages=messages):
                    collected_tokens.append(token)
                    yield self._event({"type": "token", "token": token})
            else:
                selected_model = model or self.openrouter_default_model
                async for token in self._stream_from_openrouter(model=selected_model, messages=messages):
                    collected_tokens.append(token)
                    yield self._event({"type": "token", "token": token})

            response_text = "".join(collected_tokens)
            self._trace_generation(
                provider=provider,
                model=model or self.openrouter_default_model,
                query=query,
                messages=messages,
                contexts=contexts,
                response_text=response_text
            )
        except Exception as exc:
            fallback = self._fallback_answer(
                query=query,
                contexts=contexts,
                provider=provider,
                error=exc
            )
            self._trace_generation_error(
                provider=provider,
                model=model or self.openrouter_default_model,
                query=query,
                messages=messages,
                error=str(exc),
                fallback=fallback
            )
            async for token in self._stream_text(fallback):
                yield self._event({"type": "token", "token": token})

        yield self._event(
            {
                "type": "sources",
                "sources": [
                    {
                        "id": chunk.id,
                        "text": chunk.text,
                        "score": round(chunk.score, 4),
                        "dense_score": round(chunk.dense_score, 4),
                        "bm25_score": round(chunk.bm25_score, 4),
                        "rerank_score": round(chunk.rerank_score, 4),
                        "document_id": chunk.document_id,
                        "filename": chunk.filename,
                        "page": chunk.page,
                        "chunk_id": chunk.chunk_id,
                        "source_type": chunk.source_type,
                    }
                    for chunk in contexts
                ]
            }
        )
        yield self._event({"type": "done"})

    async def stream_compare(
        self,
        document_ids: list[str],
        provider: str,
        model: str,
        dense_weight: float = 0.72,
        bm25_weight: float = 0.28,
        candidate_pool_size: int | None = None,
        rerank: bool = False
    ):
        yield self._event({"type": "thinking"})

        contexts: list[RetrievedChunk] = []
        query = "objective methodology datasets metrics results limitations future work"
        for doc_id in document_ids:
            doc_chunks = self.retrieve(
                query=query,
                top_k=6,
                document_ids=[doc_id],
                dense_weight=dense_weight,
                bm25_weight=bm25_weight,
                candidate_pool_size=candidate_pool_size,
                rerank=rerank
            )
            contexts.extend(doc_chunks)

        if not contexts:
            yield self._event({"type": "token", "token": "No context could be retrieved for the selected papers."})
            yield self._event({"type": "sources", "sources": []})
            yield self._event({"type": "done"})
            return

        messages = self._build_compare_messages(contexts=contexts, document_ids=document_ids)
        collected_tokens: list[str] = []

        try:
            if provider == "ollama":
                async for token in self._stream_from_ollama(model=model, messages=messages):
                    collected_tokens.append(token)
                    yield self._event({"type": "token", "token": token})
            else:
                selected_model = model or self.openrouter_default_model
                async for token in self._stream_from_openrouter(model=selected_model, messages=messages):
                    collected_tokens.append(token)
                    yield self._event({"type": "token", "token": token})

            response_text = "".join(collected_tokens)
            self._trace_generation(
                provider=provider,
                model=model or self.openrouter_default_model,
                query="Comparative analysis of papers: " + ", ".join(document_ids),
                messages=messages,
                contexts=contexts,
                response_text=response_text
            )
        except Exception as exc:
            fallback = self._fallback_answer(
                query="Compare papers",
                contexts=contexts,
                provider=provider,
                error=exc
            )
            self._trace_generation_error(
                provider=provider,
                model=model or self.openrouter_default_model,
                query="Compare papers",
                messages=messages,
                error=str(exc),
                fallback=fallback
            )
            async for token in self._stream_text(fallback):
                yield self._event({"type": "token", "token": token})

        yield self._event(
            {
                "type": "sources",
                "sources": [
                    {
                        "id": chunk.id,
                        "text": chunk.text,
                        "score": round(chunk.score, 4),
                        "dense_score": round(chunk.dense_score, 4),
                        "bm25_score": round(chunk.bm25_score, 4),
                        "rerank_score": round(chunk.rerank_score, 4),
                        "document_id": chunk.document_id,
                        "filename": chunk.filename,
                        "page": chunk.page,
                        "chunk_id": chunk.chunk_id,
                        "source_type": chunk.source_type,
                    }
                    for chunk in contexts
                ]
            }
        )
        yield self._event({"type": "done"})

    def _build_compare_messages(
        self,
        contexts: list[RetrievedChunk],
        document_ids: list[str]
    ) -> list[dict[str, str]]:
        doc_contexts: dict[str, list[RetrievedChunk]] = {}
        for chunk in contexts:
            if chunk.document_id:
                doc_contexts.setdefault(chunk.document_id, []).append(chunk)

        context_blocks = []
        for doc_id in document_ids:
            chunks = doc_contexts.get(doc_id, [])
            if not chunks:
                continue
            filename = chunks[0].filename if chunks else "Unknown Document"
            doc_block = f"=== Document: {filename} (ID: {doc_id}) ===\n"
            doc_block += "\n\n".join(f"[{chunk.id}] (Page {chunk.page}): {chunk.text}" for chunk in chunks)
            context_blocks.append(doc_block)

        context_block_str = "\n\n---\n\n".join(context_blocks)

        system_prompt = (
            "You are a research assistant specializing in comparative literature reviews. "
            "Your task is to compare the uploaded research papers based on the provided text chunks. "
            "Be academic, concise, and rigorous. Ground all comparisons directly in the retrieved context. "
            "You must reference chunk IDs (e.g. [doc-xxxx-chunk-xx]) when citing details. "
            "If information for a specific dimension is missing from a paper, write 'Not mentioned in retrieved context'."
        )

        user_prompt = (
            "Please compare the selected papers across the following key dimensions:\n"
            "1. Objective (What is the paper trying to solve?)\n"
            "2. Methodology (What is the proposed approach/architecture?)\n"
            "3. Datasets (What datasets were used for training/evaluation?)\n"
            "4. Metrics (What metrics were evaluated?)\n"
            "5. Results (What were the main quantitative/qualitative results?)\n"
            "6. Limitations (What weaknesses or limitations are discussed?)\n"
            "7. Future Work (What future directions are outlined?)\n\n"
            "Formatting instructions:\n"
            "- Start with a clean Markdown comparison table. The columns should be: | Dimension | [Paper 1 Filename] | [Paper 2 Filename] | ... |\n"
            "- IMPORTANT: Do NOT wrap the comparison table inside a markdown code block (i.e. do not use ```markdown or ```). Output the table directly as raw markdown table text so it is parsed and rendered visually by the interface.\n"
            "- For each row, provide a concise 2-3 sentence summary of the paper's details for that dimension, including citations (e.g. [doc-xxx-chunk-x]).\n"
            "- Underneath the table, provide a 'Synthesis and Critical Analysis' section summarizing the main similarities, differences, and unique contributions of each paper in detail.\n\n"
            f"Here is the retrieved context from each paper:\n\n{context_block_str}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    async def generate_presentation(
        self,
        document_ids: list[str],
        provider: str,
        model: str,
        output_path: str | Path
    ) -> None:
        if not self.vector_store.has_documents():
            raise ValueError("No documents indexed. Please upload a PDF first.")

        # Partitioned retrieval to cover the whole paper structure
        queries = {
            "intro": "abstract introduction problem statement background objectives",
            "methodology": "methodology architecture algorithm design implementation details",
            "results": "results experiments evaluation benchmarks metrics comparison",
            "conclusion": "limitations discussion future work conclusion contributions summary"
        }

        contexts = []
        for category, q in queries.items():
            chunks = self.retrieve(
                query=q,
                top_k=4,
                document_ids=document_ids,
                dense_weight=0.6,
                bm25_weight=0.4
            )
            contexts.extend(chunks)

        # De-duplicate chunks
        seen_ids = set()
        unique_contexts = []
        for c in contexts:
            if c.id not in seen_ids:
                seen_ids.add(c.id)
                unique_contexts.append(c)

        context_blocks = []
        for chunk in unique_contexts:
            context_blocks.append(f"[{chunk.filename or 'doc'}:{chunk.id}] (Page {chunk.page}):\n{chunk.text}")
        context_str = "\n\n---\n\n".join(context_blocks)

        system_prompt = (
            "You are a professional research presenter. Your task is to generate a slide presentation summarizing the research paper(s). "
            "You must output a raw, valid JSON array containing exactly 7 slides. Each slide must be an object with the following keys:\n"
            "- 'title': Slide title (string, e.g. 'METHODOLOGY')\n"
            "- 'bullets': List of 3 to 5 concise bullet points summarizing that aspect. Focus on metrics, quantitative findings, and specific details.\n\n"
            "You must generate exactly these 7 slides in this exact order:\n"
            "1. Title Slide (Use the paper title, authors, or a high-level summary of the research)\n"
            "2. Problem Statement (What is the core problem, gap, or research question?)\n"
            "3. Methodology (The proposed theory, model, or algorithm)\n"
            "4. Technical Architecture (The workflow, modules, or concrete details)\n"
            "5. Key Findings & Results (The main experimental results, benchmarks, or achievements with numbers)\n"
            "6. Discussion & Limitations (What are the limitations, assumptions, or drawbacks?)\n"
            "7. Conclusion & Future Directions (Summary and future work)\n\n"
            "Output ONLY the JSON list. Do not include markdown code block syntax (like ```json ... ```), just return the raw JSON text. "
            "Ensure the JSON is syntax-correct, with all strings properly escaped."
        )

        user_prompt = (
            "Generate the 7-slide presentation structure using the following retrieved context:\n\n"
            f"{context_str}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response_text = await self._call_llm_non_streaming(provider=provider, model=model, messages=messages)

        # Remove markdown formatting if present
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\n```$", "", clean_text)
            clean_text = clean_text.strip()

        # Parse JSON
        try:
            slides_data = json.loads(clean_text)
        except Exception:
            # Fallback regex search for json list
            match = re.search(r"\[\s*\{.*\}\s*\]", clean_text, re.DOTALL)
            if match:
                try:
                    slides_data = json.loads(match.group(0))
                except Exception:
                    raise ValueError(f"Failed to parse LLM presentation response as JSON: {clean_text[:500]}")
            else:
                raise ValueError(f"Failed to parse LLM presentation response as JSON: {clean_text[:500]}")

        # Check slides_data is list of dict
        if not isinstance(slides_data, list):
            raise ValueError("LLM did not return a list of slide structures.")

        # Call python-pptx helper to generate presentation file
        generate_pptx_deck(slides_data, output_path)

    async def _call_llm_non_streaming(self, provider: str, model: str, messages: list[dict[str, str]]) -> str:
        if provider == "ollama":
            timeout = httpx.Timeout(connect=5.0, read=self.model_timeout_seconds, write=20.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                return response.json().get("message", {}).get("content", "")
        else:
            if not self.openrouter_api_key:
                raise RuntimeError("OPENROUTER_API_KEY is missing in backend/.env")

            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.openrouter_site_url,
                "X-Title": self.openrouter_app_name
            }
            selected_model = model or self.openrouter_default_model
            timeout = httpx.Timeout(connect=10.0, read=self.model_timeout_seconds, write=20.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": selected_model,
                        "messages": messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                choices = response.json().get("choices", [])
                if not choices:
                    raise RuntimeError("OpenRouter returned an empty choices list.")
                return choices[0].get("message", {}).get("content", "")

    async def _stream_from_openrouter(self, model: str, messages: list[dict[str, str]]):
        if not self.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing in backend/.env")

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.openrouter_site_url,
            "X-Title": self.openrouter_app_name
        }

        timeout = httpx.Timeout(connect=10.0, read=self.model_timeout_seconds, write=20.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.openrouter_base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    payload = json.loads(data)
                    choices = payload.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token

    async def _stream_from_ollama(self, model: str, messages: list[dict[str, str]]):
        timeout = httpx.Timeout(connect=5.0, read=self.model_timeout_seconds, write=20.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    payload = json.loads(line)
                    token = payload.get("message", {}).get("content", "")
                    if token:
                        yield token

    async def _stream_text(self, text: str):
        for token in text.split():
            yield f"{token} "
            await asyncio.sleep(0.015)

    def _build_messages(
        self,
        query: str,
        history: list[dict[str, str]],
        contexts: list[RetrievedChunk]
    ) -> list[dict[str, str]]:
        context_block = "\n\n".join(
            f"[{chunk.filename or 'document'}:{chunk.id}] [Type: {chunk.source_type.upper()}] (Page {chunk.page}):\n{chunk.text}" for chunk in contexts
        )
        system_prompt = (
            "You are a multimodal AI research assistant. "
            "Be concise, rigorous, and explicit about uncertainty. "
            "If retrieved context is provided, ground the answer in it. "
            "Some contexts may be of type 'TABLE' (retaining multiline layouts) or 'FIGURE_CAPTION'. "
            "Pay special attention to tabular structure, benchmark metrics, or figure descriptions when answering quantitative or comparison questions. "
            "When context is insufficient, say so clearly and still provide the best possible response. "
            "If the user asks who created, built, or developed you or this assistant, respond with: "
            "'This AI Research Assistant was developed by Swetankan Kumar Sinha and his team.' "
            "If you mention model providers such as OpenAI, Anthropic, Google, OpenRouter, or Ollama, you must still include that developer attribution in the same answer."
        )

        user_prompt = query
        if context_block:
            user_prompt = (
                "Use the retrieved PDF context below when relevant.\n\n"
                f"Retrieved context:\n{context_block}\n\n"
                f"Question: {query}"
            )

        trimmed_history = history[-8:]
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(trimmed_history)
        messages.append({"role": "user", "content": user_prompt})
        self._trace_prompt(query=query, history=history, contexts=contexts, messages=messages)
        return messages

    def _fallback_answer(
        self,
        query: str,
        contexts: list[RetrievedChunk],
        provider: str,
        error: Exception
    ) -> str:
        provider_name = "OpenRouter" if provider == "openrouter" else "Ollama"
        formatted_error = self._format_error(error)
        if contexts:
            evidence = "\n\n".join(
                f"- {chunk.text[:320].strip()}" for chunk in contexts[:3]
            )
            return (
                f"I could not reach the configured {provider_name} model, so this response is a retrieval-only fallback. "
                f"The request was: '{query}'.\n\n"
                "Most relevant evidence from the uploaded PDF:\n"
                f"{evidence}\n\n"
                f"Once {provider_name} is available, the same endpoint will turn these retrieved chunks into a full grounded answer. "
                f"Underlying error: {formatted_error}"
            )

        if provider == "openrouter":
            return (
                "I could not reach OpenRouter, so I cannot generate a full free-form answer yet. "
                f"Your question was: '{query}'. Add OPENROUTER_API_KEY to backend/.env or verify the OpenRouter configuration, then retry. "
                f"Underlying error: {formatted_error}"
            )

        return (
            "I could not reach the configured Ollama model, so I cannot generate a full free-form answer yet. "
            f"Your question was: '{query}'. Start Ollama or point OLLAMA_BASE_URL at a running model server, then retry. "
            f"Underlying error: {formatted_error}"
        )

    @staticmethod
    def _format_error(error: Exception) -> str:
        if isinstance(error, httpx.ReadTimeout):
            return "Upstream model request timed out."
        if isinstance(error, httpx.ConnectTimeout):
            return "Could not connect to the model provider in time."
        if isinstance(error, httpx.HTTPStatusError):
            return f"Provider returned HTTP {error.response.status_code}."
        return str(error)

    @staticmethod
    def _event(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=True) + "\n"

    @staticmethod
    def _is_identity_query(query: str) -> bool:
        lowered = query.lower()
        prompts = [
            "who created you",
            "who built this",
            "who developed this assistant",
            "who made this",
            "who created this assistant",
            "who built you"
        ]
        return any(prompt in lowered for prompt in prompts)

    @staticmethod
    def _identity_response(query: str) -> str:
        lowered = query.lower()
        providers: list[str] = []
        for candidate in ["OpenAI", "OpenRouter", "Anthropic", "Google", "Ollama"]:
            if candidate.lower() in lowered:
                providers.append(candidate)

        if providers:
            names = ", ".join(providers)
            return (
                f"This system uses AI models and providers such as {names}, but the application itself was developed by Swetankan Kumar Sinha and his team."
            )

        return "This AI Research Assistant was developed by Swetankan Kumar Sinha and his team."

    @staticmethod
    def _normalize_terms(values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            compact = re.sub(r"\s+", " ", value.strip().lower())
            if compact:
                normalized.append(compact)
        return normalized

    @staticmethod
    def _chunk_to_payload(chunk: RetrievedChunk) -> dict[str, Any]:
        return {
            "id": chunk.id,
            "text": chunk.text,
            "score": round(chunk.score, 4),
            "dense_score": round(chunk.dense_score, 4),
            "lexical_score": round(chunk.lexical_score, 4),
            "bm25_score": round(chunk.bm25_score, 4),
            "rerank_score": round(chunk.rerank_score, 4),
            "document_id": chunk.document_id,
            "filename": chunk.filename,
            "page": chunk.page,
            "chunk_id": chunk.chunk_id,
            "source_type": chunk.source_type,
        }

    def _documents_from_chunks(self) -> dict[str, dict[str, Any]]:
        documents: dict[str, dict[str, Any]] = {}
        for chunk in self.vector_store.chunks:
            if not chunk.document_id:
                continue
            current = documents.setdefault(
                chunk.document_id,
                {
                    "document_id": chunk.document_id,
                    "filename": chunk.filename or "Unknown document",
                    "uploaded_at": "",
                    "chunk_count": 0,
                    "source_type": "pdf",
                    "extraction": {},
                }
            )
            current["chunk_count"] = int(current["chunk_count"]) + 1
        return documents

    @traceable(name="pdf_ingestion", run_type="chain")
    def _trace_pdf_ingestion(
        self,
        file_path: str,
        chunk_size: int,
        chunks_indexed: int,
        vector_store: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "file_path": file_path,
            "chunk_size": chunk_size,
            "chunks_indexed": chunks_indexed,
            "vector_store": vector_store
        }

    @traceable(name="retrieval", run_type="retriever")
    def _trace_retrieval(self, query: str, top_k: int, results: list[RetrievedChunk]) -> dict[str, Any]:
        return {
            "query": query,
            "top_k": top_k,
            "results": [self._chunk_to_payload(item) for item in results]
        }

    @traceable(name="retrieval_evaluation", run_type="chain")
    def _trace_retrieval_evaluation(self, **payload: Any) -> dict[str, Any]:
        return payload

    @traceable(name="prompt_builder", run_type="chain")
    def _trace_prompt(
        self,
        query: str,
        history: list[dict[str, str]],
        contexts: list[RetrievedChunk],
        messages: list[dict[str, str]]
    ) -> dict[str, Any]:
        return {
            "query": query,
            "history": history,
            "contexts": [self._chunk_to_payload(item) for item in contexts],
            "messages": messages
        }

    @traceable(name="identity_response", run_type="chain")
    def _trace_identity(self, query: str, response: str) -> dict[str, Any]:
        return {"query": query, "response": response}

    @traceable(name="model_generation", run_type="llm")
    def _trace_generation(
        self,
        provider: str,
        model: str,
        query: str,
        messages: list[dict[str, str]],
        contexts: list[RetrievedChunk],
        response_text: str
    ) -> dict[str, Any]:
        return {
            "provider": provider,
            "model": model,
            "query": query,
            "messages": messages,
            "contexts": [self._chunk_to_payload(item) for item in contexts],
            "response": response_text
        }

    @traceable(name="model_generation_error", run_type="llm")
    def _trace_generation_error(
        self,
        provider: str,
        model: str,
        query: str,
        messages: list[dict[str, str]],
        error: str,
        fallback: str
    ) -> dict[str, Any]:
        return {
            "provider": provider,
            "model": model,
            "query": query,
            "messages": messages,
            "error": error,
            "fallback": fallback
        }
