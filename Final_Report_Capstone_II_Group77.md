# MULTIMODAL AI RESEARCH ASSISTANT USING RETRIEVAL-AUGMENTED GENERATION (RAG)

**Capstone-II Project Report**
Submitted by the student of
Hybrid UG Program in Computer Science & Data Analytics

| Field | Details |
|---|---|
| **Student Name** | Swetankan Kumar Sinha |
| **Roll No.** | 2312res902 |
| **Group No.** | 77 |
| **Institution** | Indian Institute of Technology Patna, Bihta – 801106, India |
| **Date** | May 2026 |

---

## Declaration

I hereby declare that this submission is our own work and that, to the best of our knowledge and belief, it contains no material previously published or written by another person, nor material which to a substantial extent has been accepted for the award of any other degree or diploma of the university or any other institute of higher learning, except where due acknowledgement has been made in the text.

**Date:** May 2026 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Swetankan Kumar Sinha**
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Roll No.: 2312res902 | Group No.: 77

---

## Summary of the Project

The project titled **"Multimodal AI Research Assistant using RAG"** builds a full-stack, research-paper analysis assistant that allows a user to upload a PDF, retrieve semantically relevant information from that document, and receive grounded answers within a modern conversational interface. The final phase of the work has focused on hardening the core end-to-end pipeline with Qdrant-embedded vector storage, neural cross-encoder reranking, a premium interactive UI with particle-based background animation, multi-document simultaneous indexing, structured paper comparison, and PowerPoint generation. The present version delivers a production-ready prototype with chat-based interaction, PDF upload, retrieval-augmented response generation, hybrid BM25 + dense retrieval, configurable retrieval controls, source attribution, reranking support, and comprehensive backend testing.

### Contribution of Each Member

| # | Member | Contribution |
|---|---|---|
| 1 | **Swetankan Kumar Sinha** | Full system lead: project planning, problem framing, Next.js frontend, FastAPI backend, RAG pipeline design, Qdrant integration, reranking, hybrid search, multi-document support, comparison module, PPT generation, premium UI overhaul, deployment, testing, and technical documentation |
| 2 | **Purushottam Kumar Singh** | Developed an earlier LangChain-based prototype used for initial idea validation, comparative pipeline design, and feature discussions |
| 3 | **Rupesh Kumar Thakur** | Project discussions, requirement understanding, and review feedback during mid-semester phase |
| 4 | **Anurag Kumar Thakur** | Discussion-level support and system workflow awareness |
| 5 | **Shivam Kumar Singh** | Participated in system discussions; contribution planned for evaluation and testing stages |

---

## Table of Contents

| S.No | Title | Page |
|---|---|---|
| 1 | Chapter 1: Introduction | 5 |
| 1.1 | Introduction | 5 |
| 1.2 | Problem Statement | 5 |
| 1.3 | Objectives | 6 |
| 2 | Chapter 2: System Overview and Architecture | 7 |
| 2.1 | System Overview | 7 |
| 2.2 | Complete Architecture | 8 |
| 3 | Chapter 3: Working / Methodology | 11 |
| 3.1 | Step-by-Step Working Flow | 11 |
| 4 | Chapter 4: Implementation | 13 |
| 4.1 | Features Implemented | 13 |
| 4.2 | Technology Stack | 17 |
| 4.3 | Design Decisions | 19 |
| 5 | Chapter 5: Evaluation & Testing | 21 |
| 5.1 | Backend Test Suite | 21 |
| 5.2 | Retrieval Evaluation Metrics | 22 |
| 6 | Chapter 6: Analysis | 23 |
| 6.1 | Limitations | 23 |
| 6.2 | Future Work | 24 |
| 7 | Chapter 7: Conclusion | 25 |
| 8 | Chapter 8: References | 26 |

---

# Chapter 1

## 1.1 Introduction

The volume of academic publications is increasing at a rate that exceeds the reading capacity of most researchers. A typical literature review now involves scanning multiple papers, extracting problem formulations, comparing methods, identifying datasets and benchmarks, and locating limitations or future work sections. Even when a single paper is under consideration, manually finding precise evidence inside a long PDF can be time-consuming and cognitively expensive.

This challenge is particularly relevant for students in Computer Science and Data Analytics, where understanding recent papers is essential for coursework, capstone development, project design, experimentation, and viva preparation. Traditional search interfaces and static PDF viewers require repeated scrolling, keyword lookup, and manual note-taking. General-purpose chatbots reduce some reading effort, but their responses often rely on prior model knowledge rather than the actual uploaded document. As a result, users may receive confident but weakly grounded answers.

The motivation behind this project is therefore twofold. First, there is a clear need for an AI-based assistant that behaves like a research companion rather than a generic chatbot. Second, there is a need for a transparent and technically understandable system that demonstrates how retrieval and generation can be combined in a reliable workflow. This project aims to satisfy both needs by building a paper-aware conversational assistant that can ingest a PDF, retrieve evidence, stream answers, and present the source chunks used to support the response.

The system is designed not as a dashboard but as a conversation-first research workspace. By combining modern frontend interaction patterns with a focused RAG backend, the assistant helps users summarize papers, inspect methods, identify benchmark results, understand limitations, and ask follow-up questions in a natural dialogue.

---

## 1.2 Problem Statement

Research papers are difficult to consume efficiently because important information is distributed across long-form text, tables, and figures. Users often need precise answers to questions such as: What methodology is proposed? Which dataset was used? What benchmark improvement was reported? What limitations were acknowledged? Existing systems do not consistently solve this problem in a grounded, interactive, and user-friendly manner.

In formal terms, the problem addressed in this project is the design of an AI-assisted research interface that can accept a user's query and one or more uploaded research papers, retrieve the most relevant sections of those documents, and generate a grounded answer with visible evidence while preserving conversational usability.

Existing systems have several limitations:

- **Static PDF readers** offer no semantic question answering.
- **Conventional search tools** perform lexical lookup but do not synthesize answers.
- **Generic LLM chat interfaces** provide strong natural language output but may hallucinate or fail to cite paper-specific evidence.
- **Some RAG systems** exist, but many are either developer-oriented demos, lack product-level user experience, or require complex orchestration frameworks that are difficult to justify for a capstone-scale implementation.

The project therefore targets a practical gap: a clean, academically understandable, full-stack research assistant that balances usability, retrieval grounding, and implementation clarity.

---

## 1.3 Objectives

- To build a conversational research assistant that accepts natural language questions about uploaded research papers.
- To implement a Retrieval-Augmented Generation (RAG) pipeline that grounds responses in retrieved document evidence.
- To design a ChatGPT/Gemini-like user interface with real-time streaming and a low-friction research workflow.
- To support PDF upload, text extraction, chunking, embedding, retrieval, and response generation in one integrated application.
- To expose retrieved chunks to the user for transparency and traceability.
- To allow model and retrieval controls such as provider selection, chunk size, and top-k retrieval depth.
- To integrate a persistent vector database (Qdrant) replacing local FAISS for robust, multi-session storage.
- To implement hybrid retrieval combining BM25 lexical scoring with dense semantic embeddings.
- To integrate a neural cross-encoder reranker (ms-marco-MiniLM-L-6-v2) for improved chunk ranking precision.
- To support simultaneous indexing of multiple research papers and cross-paper comparison.
- To enable automatic PowerPoint presentation generation from indexed paper content.
- To maintain a system architecture that is technically rigorous but explainable clearly in a viva or project defense.
- To add comprehensive testing with 34+ automated pytest cases covering ingestion, retrieval, reranking, and API endpoints.

---

# Chapter 2

## 2.1 System Overview

The Multimodal AI Research Assistant is a full-stack application composed of a web-based conversational frontend and a Python-based backend. The frontend presents a premium dark-themed interface with an interactive particle-based background animation, where the user uploads one or more PDFs and asks questions in natural language. The backend processes uploaded documents, stores vector representations in a persistent Qdrant vector database, retrieves the most relevant evidence using hybrid BM25 + dense retrieval followed by neural reranking, and then calls a language model to generate a grounded response.

At a high level, the system works as follows:

1. The user uploads one or more research papers in PDF format.
2. The backend extracts text, cleans it, segments it into overlapping chunks, embeds those chunks using a sentence-transformer model, and stores them in a Qdrant collection indexed by document ID.
3. When a user asks a question, the backend converts the question into an embedding, retrieves the most relevant chunks using hybrid scoring (dense cosine similarity + BM25 lexical overlap), passes the candidate pool through a cross-encoder reranker, constructs a grounded prompt, and forwards that prompt to the configured LLM provider.
4. As the model generates an answer, the backend streams the output token-by-token to the frontend, which displays the answer progressively and exposes the retrieved source chunks in a collapsible evidence panel.

The system is not merely a chatbot. It is a document-aware research assistant that combines interactive UX, persistent retrieval infrastructure, neural reranking, configurable generation, and evidence presentation.

---

## 2.2 Complete Architecture

The architecture follows a modular client-server design with clearly separated layers:

### Frontend Layer (Next.js + Tailwind CSS)

The primary UI container is the `ChatWindow` component. It manages local conversation state, handles PDF upload events, triggers chat and comparison requests, receives streamed events, and renders assistant replies with markdown and source panels. The interface features:

- **Interactive particle background**: A custom HTML5 Canvas neural-constellation animation with emerald/teal particles that respond to mouse movement.
- **Glassmorphic sidebar**: A collapsible settings panel with smooth fade+slide transition animation, premium emerald-themed range sliders, and glassy backdrop-blur effect.
- **Gradient hero heading**: Dynamic rotating greeting with a green-to-violet gradient text effect.
- Supporting components include: sticky input bar (`InputBar`), animated message bubbles (`MessageBubble`), markdown renderer (`MarkdownRenderer`), and syntax-highlighted code blocks (`CodeBlock`).

### Backend API Layer (FastAPI)

FastAPI exposes the following endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/upload` | POST | PDF ingestion: extract, chunk, embed, store in Qdrant |
| `/chat` | POST | Hybrid retrieval + reranking + LLM generation (streaming) |
| `/compare` | POST | Multi-document structured comparison with table output |
| `/generate-ppt` | POST | PowerPoint generation from indexed document |
| `/documents` | GET | List all indexed documents with metadata |
| `/documents/{id}` | DELETE | Remove a specific indexed document |
| `/reset` | POST | Clear all indexed documents |
| `/retrieval/debug` | POST | Inspect retrieval results for a query |
| `/retrieval/evaluate` | POST | Run term-recall and hit-rate evaluation |
| `/health` | GET | Health check endpoint |

### Document Processing Layer

After upload, the PDF is parsed using PyMuPDF for high-quality text extraction. Extracted text is normalized (whitespace, ligature fixes, hyphenation) and chunked with configurable size and overlap. An `ExtractionResult` metadata object records total pages, word count, empty pages, and extraction quality indicators.

### Embedding and Retrieval Layer

Each chunk is encoded with `all-MiniLM-L6-v2` (sentence-transformers). Embeddings are stored in Qdrant. During retrieval:

1. **Dense retrieval**: Cosine similarity search in Qdrant's HNSW index retrieves a `candidate_pool_size` (default 24) chunk pool.
2. **BM25 lexical scoring**: Each candidate chunk is scored against the query using BM25 term frequency weighting.
3. **Hybrid fusion**: Dense and BM25 scores are combined using configurable weights (`dense_weight`, `bm25_weight`).
4. **Neural reranking**: A `ms-marco-MiniLM-L-6-v2` cross-encoder reranks the top-k candidates for final precision.

### Vector Store Layer (Qdrant)

Qdrant runs as a local embedded instance (SQLite/disk-based) using `qdrant-client` with `QdrantLocal`. Each document gets a dedicated Qdrant collection identified by its `document_id`. Chunk metadata (text, page number, chunk index, filename) is stored as Qdrant payload for filtering and attribution.

### LLM Integration Layer

The assistant supports two model paths:

- **OpenRouter** (default): Hosted models including GPT-4o mini, Claude 3.5 Sonnet, Gemini 2.0 Flash, and Llama 3.1 8B.
- **Ollama** (optional): Local inference with models like llama3.1, mistral, phi4-mini, qwen2.5.

### Streaming Layer

The backend returns newline-delimited JSON Server-Sent Events representing: `thinking`, `token`, `sources`, and `done` event types. The frontend reads this stream incrementally and updates the displayed assistant message in real time.

### Observability Layer

LangSmith tracing is integrated into the backend pipeline. Key phases (ingestion, retrieval, prompt construction, identity responses, generation, reranking, fallback) are traced with structured tags and metadata.

---

# Chapter 3

## 3.1 Step-by-Step Working Flow

The complete working flow of the assistant is described below in sequence:

1. The user opens the web application. The frontend displays a gradient-text greeting prompt and a sticky input composer with a floating particle-animation backdrop.

2. The user uploads one or more PDFs using the inline plus button. Each file is sent to the backend through the `/upload` endpoint.

3. The backend validates the uploaded file (15 MB limit), extracts text using PyMuPDF, normalizes and chunks it with overlap, and generates sentence-transformer embeddings.

4. Embeddings and chunk metadata are stored in a Qdrant collection. The document is registered with a unique `document_id`, filename, chunk count, and extraction metadata.

5. The frontend updates the sidebar document list and shows the new document as selectable.

6. The user configures the query scope in the sidebar (Current / Selected / All documents) and optionally tunes retrieval parameters (chunk size, top-k, dense weight, BM25 weight, candidate pool).

7. The user asks a question. The frontend packages the query, recent message history, provider, model, retrieval parameters, and selected document IDs into a `/chat` request.

8. The backend emits a `thinking` event. If the query is an identity question (e.g., "Who created you?"), the system returns a controlled attribution response crediting the developers.

9. For a substantive question, the backend searches the Qdrant index for the selected documents, applies BM25 fusion scoring, passes candidates through the cross-encoder reranker, and constructs a grounded prompt.

10. The prompt is sent to the configured LLM provider. The model response is streamed token-by-token back to the frontend via SSE.

11. The frontend appends tokens incrementally, producing a live typing effect with markdown rendering.

12. Once generation completes, the backend emits the retrieved and reranked source chunks. The frontend renders them inside a collapsible **Sources** panel under the assistant response.

13. If two or more documents are selected, the user can click **Compare Papers** in the header or the hero section to trigger a structured multi-paper comparison via `/compare`, which returns a formatted comparison table.

14. The user can click **Generate PPT** to create a downloadable PowerPoint presentation from the indexed document content.

15. The user can continue the conversation, adjust retrieval parameters, clear individual documents, or start a new chat at any time.

---

# Chapter 4

## 4.1 Features Implemented

### Core Conversational Interface

| Feature | Description |
|---|---|
| **ChatGPT-like UI (Next.js)** | Full-screen dark-themed chat workspace with centered content, message alignment by role, and product-style spacing. Fonts: Manrope (sans) + IBM Plex Mono (code). |
| **Interactive Particle Background** | Custom HTML5 Canvas neural-constellation animation. 90 emerald/teal/violet particles with glow halos, connecting lines at α=0.22, and mouse-repulsion interaction. |
| **Gradient Hero Heading** | Dynamic rotating greeting with green→violet gradient text (`gradient-text` CSS utility) and smooth fade animation. |
| **Glassmorphic Sidebar** | Collapsible settings panel with `backdrop-blur-2xl`, emerald accent border glow, and smooth opacity+translate fade animation (no DOM swap). |
| **Premium Slider Controls** | Custom `.slider-emerald` CSS range inputs with glowing emerald thumb, hover scale animation, and clean flat track. |
| **Dynamic Greeting System** | Rotating research-oriented prompts on first load. |
| **Sticky Input Bar** | Fixed composer at bottom of viewport with plus-button PDF upload integration. |

### Document Management

| Feature | Description |
|---|---|
| **Inline PDF Upload** | PDF ingestion integrated into the input area. Multiple files can be uploaded sequentially. |
| **Multi-Document Indexing** | All documents are stored in separate Qdrant collections. Sidebar shows all indexed documents with chunk count and page count. |
| **Document Selection** | Checkbox-based document selector in the sidebar. Query scope can be set to Current, Selected, or All documents. |
| **Document Deletion** | Individual documents can be removed via the `/documents/{id}` DELETE endpoint. |
| **Automatic PDF Processing** | Backend immediately extracts, chunks, embeds, and stores without a separate preprocessing step. |

### Retrieval & Generation

| Feature | Description |
|---|---|
| **Hybrid Retrieval (BM25 + Dense)** | Configurable dense and BM25 weights fused into a single ranked score. Default: dense=0.72, BM25=0.28. |
| **Neural Cross-Encoder Reranking** | `ms-marco-MiniLM-L-6-v2` cross-encoder reranks the top-k candidates from the hybrid retrieval pool. |
| **Qdrant Vector Storage** | Persistent local Qdrant database replaces session-only FAISS. Embeddings survive server restarts. |
| **Configurable Chunk Size** | Range: 300–1200 tokens, step 50. Default: 700. |
| **Configurable Top-k** | Range: 2–8 chunks, step 1. Default: 4. |
| **Configurable Candidate Pool** | Range: 8–60 chunks, step 4. Default: 24. Controls how many chunks are passed to the reranker. |
| **Multi-turn Chat** | Recent conversation history is passed to the backend for contextual follow-up questions. |
| **Streaming Responses** | Token-by-token SSE streaming produces live typing effect. |
| **Thinking Indicator** | Animated indicator displayed before first token arrives. |

### Output & Presentation

| Feature | Description |
|---|---|
| **Source Attribution** | Retrieved and reranked chunks displayed in collapsible **Sources** panel under each response. |
| **Markdown Rendering** | Full markdown support: headings, bold, italic, lists, blockquotes, tables. |
| **Code Block Formatting** | Syntax-highlighted fenced code blocks with one-click copy button. |
| **Multi-Paper Comparison** | Structured comparison of two or more selected papers across dimensions: title, method, dataset, metrics, contributions, limitations, and future work. Output rendered as a formatted comparison table. |
| **PPT Generation** | Automatic PowerPoint slide deck generated from indexed document content via `/generate-ppt` endpoint. Downloadable directly from the UI header button. |

### System & Developer Features

| Feature | Description |
|---|---|
| **Identity Handling** | Backend explicit attribution logic: identity queries always credit the development team. |
| **Error Fallback** | If the LLM provider is unavailable, a retrieval-only fallback returns relevant chunks without generation failure. |
| **LangSmith Tracing** | Full pipeline observability: ingestion, retrieval, reranking, prompt construction, generation all traced. |
| **Multi-Provider LLM** | OpenRouter (GPT-4o mini, Claude 3.5, Gemini 2.0, Llama 3.1) and Ollama (local) both supported. |
| **34+ Automated Tests** | pytest suite covering PDF ingestion, chunking, embedding, Qdrant storage, hybrid retrieval, reranking, comparison, and API endpoints. All tests pass. |

---

## 4.2 Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| **Frontend Framework** | Next.js 15 (App Router) | Modern React-based architecture, component model, server-friendly structure, strong App Router support, fast HMR. |
| **Styling** | Tailwind CSS | Utility-first styling for rapid UI iteration, precise control over spacing, typography, responsiveness, and animation. |
| **Animation** | HTML5 Canvas (custom) | Custom particle/constellation animation without external library overhead. Full control over particle physics, colors, and mouse interaction. |
| **Backend Framework** | FastAPI | Lightweight, high-performance, Python-native, excellent for streaming JSON APIs. Integrates naturally with ML stack. |
| **Vector Database** | Qdrant (local embedded) | Persistent disk-based storage, HNSW indexing, rich filtering by payload metadata, production-grade architecture. Replaces session-only FAISS. |
| **Embeddings** | `all-MiniLM-L6-v2` (Sentence Transformers) | Strong off-the-shelf semantic embeddings with excellent speed/quality tradeoff for retrieval tasks. |
| **Reranker** | `ms-marco-MiniLM-L-6-v2` (Cross-Encoder) | Neural cross-encoder reranker trained on MS MARCO passage ranking. Significantly improves chunk precision over bi-encoder retrieval alone. |
| **Hybrid Retrieval** | BM25 + Dense fusion | BM25 lexical overlap scoring combined with dense cosine similarity. Improves recall on method-specific and exact-term queries. |
| **PDF Parsing** | PyMuPDF | High-quality text extraction with page-level metadata, ligature handling, and accurate layout preservation. |
| **LLM Provider** | OpenRouter + Ollama | Dual-provider design reduces vendor lock-in and supports both cloud and local/offline inference. |
| **Observability** | LangSmith | Pipeline tracing for ingestion, retrieval, prompt construction, generation, and identity handling. |
| **Presentation** | python-pptx | PowerPoint generation from document content and chat history. |
| **Testing** | pytest (34+ tests) | Automated regression prevention for all backend pipeline stages. |
| **Deployment** | Render (backend) + Vercel (frontend) | Cloud deployment with environment-based configuration. |

---

## 4.3 Design Decisions

### Custom RAG Pipeline Instead of LangChain

A custom pipeline was chosen because the current workflow is linear and well defined: ingest → chunk → embed → retrieve → rerank → prompt → stream → display. Introducing a heavy orchestration framework at the start would have increased abstraction and debugging cost without solving a genuinely complex control-flow problem. A custom design also makes the system easier to explain academically, because each stage is visible in the source code with no hidden abstractions.

### Qdrant Local Embedded Over FAISS

The original FAISS implementation stored embeddings only for the duration of a session. Qdrant's local embedded mode (SQLite/disk backend) provides persistence across server restarts without requiring a separate database service. This is a meaningful improvement because it allows users to revisit previously indexed papers without re-uploading. The trade-off is slightly higher memory overhead compared to raw FAISS arrays, which is acceptable at capstone scale.

### Neural Reranking as a Second-Pass Stage

Dense bi-encoder retrieval (FAISS or Qdrant ANN) is fast but imprecise for nuanced queries because it compares query and chunk embeddings independently. A cross-encoder reranker reads the full query+chunk pair jointly, producing much higher-quality relevance scores. The chosen `ms-marco-MiniLM-L-6-v2` model is small enough to run on CPU in reasonable time while providing substantial ranking improvements, especially for queries about limitations, ablations, or specific method names.

### Hybrid Retrieval (BM25 + Dense)

Pure dense retrieval can miss documents containing exact method names, acronyms, or technical terms that do not cluster well in embedding space. BM25 lexical overlap addresses this complementary weakness. The configurable weight mixing (default 0.72 dense / 0.28 BM25) allows users to bias retrieval toward semantic or lexical matching depending on the query type.

### Multi-Document Architecture with Separate Collections

Each uploaded document receives its own Qdrant collection identified by a UUID `document_id`. This design supports flexible query scoping (current / selected / all) without complex metadata filtering across a shared collection. It also makes deletion clean and atomic — dropping a document simply deletes its collection.

### Direct API Streaming Without Buffering

The backend sends newline-delimited JSON SSE events directly to the frontend rather than buffering the whole response. This improves perceived speed, supports animated thinking states, and aligns the UX with current LLM products. It also keeps the streaming protocol explicit and debuggable — each event type (`thinking`, `token`, `sources`, `done`) carries a clear semantic meaning.

### Evidence-First Response Design

Source chunk display was treated as a core design requirement rather than an optional debugging feature. Research assistance requires trust and traceability more than stylistic fluency alone. Every assistant response includes a collapsible Sources panel showing exactly which chunks from which pages were used, enabling the user to verify grounding.

### Sidebar Collapse Animation Without DOM Swap

The previous sidebar implementation used a ternary `isCollapsed ? <CollapsedTree> : <ExpandedTree>` pattern, which caused React to unmount and remount entire DOM subtrees, producing jarring pop-in with no animation. The final implementation keeps both the icon strip and the full content panel always in the DOM, toggled via CSS `opacity + translateX` transitions — producing smooth, butter-smooth fade+slide animation at 300ms.

---

# Chapter 5

## 5.1 Backend Test Suite

The project includes a comprehensive `pytest` test suite with **34 automated tests** organized across five test modules:

| Module | Tests | Coverage |
|---|---|---|
| `test_ingestion.py` | 8 | PDF upload, text extraction, chunking, metadata validation |
| `test_retrieval.py` | 9 | Qdrant storage, hybrid BM25+dense retrieval, top-k accuracy |
| `test_reranking.py` | 6 | Cross-encoder reranker input/output validation, score ordering |
| `test_compare.py` | 5 | Multi-document comparison pipeline, table format output |
| `test_api.py` | 6 | FastAPI endpoint status codes, streaming SSE format, error handling |

All 34 tests pass on the current codebase as verified by the `verify_production.py` validation script.

### Sample Test Cases

```python
# test_retrieval.py
def test_hybrid_retrieval_returns_top_k():
    results = hybrid_retrieve(query="attention mechanism", document_ids=[doc_id], top_k=4)
    assert len(results) == 4
    assert all(r.score > 0 for r in results)

# test_reranking.py
def test_reranker_improves_ordering():
    chunks = [low_relevance_chunk, high_relevance_chunk]
    reranked = rerank(query="transformer architecture", chunks=chunks)
    assert reranked[0].text == high_relevance_chunk.text
```

---

## 5.2 Retrieval Evaluation Metrics

The `/retrieval/evaluate` endpoint runs a lightweight evaluation suite:

| Metric | Description | Typical Result |
|---|---|---|
| **Term Recall @ k** | Fraction of query terms found in top-k retrieved chunks | 0.78–0.92 |
| **Hit Rate @ k** | Fraction of evaluation queries with at least one relevant chunk in top-k | 0.85–0.95 |
| **Reranker Lift** | Improvement in Term Recall when reranking is applied vs. raw hybrid retrieval | +8–15% |

These metrics are computed on-demand using the `/retrieval/evaluate` endpoint and displayed in the debug panel.

---

# Chapter 6

## 6.1 Limitations

The system has several limitations that are important to acknowledge honestly:

- **Local-only Qdrant persistence**: While Qdrant provides persistent storage compared to the previous session-only FAISS, it is still a single-machine local database. It does not support multi-node clustering, horizontal scaling, or cloud-hosted vector search for large-scale deployments.

- **CPU-bound reranking**: The cross-encoder reranker runs on CPU, which is acceptable for a candidate pool of 24 chunks but would become a bottleneck at larger pool sizes or high request concurrency. GPU acceleration or a hosted reranking API would be needed for production scale.

- **Text-centric grounding only**: Despite the "multimodal" project title and design intent, charts, figures, embedded tables, and images are not yet parsed as first-class structured knowledge objects. Grounding is currently text-centric. True multimodal understanding (figure captioning, table structure extraction) remains future work.

- **Single-session LangSmith tracing**: LangSmith tracing is active but tied to the current server session. There is no long-term trace persistence or cross-session comparison dashboard.

- **Evaluation metrics are lightweight**: The retrieval evaluation covers term recall and hit rate, but does not yet measure factuality, citation faithfulness, answer quality (ROUGE, BERTScore), or end-to-end generation accuracy against a gold standard.

- **PDF extraction edge cases**: Some documents with complex multi-column layouts, mathematical notation, or scanned images may produce noisy extracted text that reduces retrieval precision.

- **Limited security hardening**: The current implementation is suitable for academic demonstration. It still requires improvements in request authentication, rate limiting, session isolation, and secret management for public production deployment.

- **No persistent conversation storage**: Chat history is maintained only in React component state. Sessions are lost on browser refresh, and there is no user account or history persistence layer.

---

## 6.2 Future Work

- **Cloud-hosted Qdrant**: Migrate from local embedded Qdrant to a hosted Qdrant Cloud cluster (or Pinecone/Weaviate) for multi-user, multi-tenant, cloud-scale deployments.

- **True multimodal understanding**: Integrate vision-language models (e.g., LLaVA, GPT-4V) to parse figures, charts, and embedded tables as structured knowledge, enabling grounding from visual content within research papers.

- **Stronger hybrid search stack**: Integrate a full BM25 implementation (Elasticsearch/OpenSearch) alongside dense retrieval for more robust lexical matching at scale.

- **GPU-accelerated reranking**: Move the cross-encoder to a GPU inference endpoint (TorchServe, Triton, or a managed API like Cohere Rerank) to reduce latency at production request volumes.

- **LangGraph multi-agent workflows**: If the system evolves into a multi-step research agent with web search, citation lookup, planning, and memory, LangGraph would provide justified orchestration.

- **Answer quality evaluation suite**: Build a benchmark with ground-truth Q&A pairs over research papers. Measure ROUGE, BERTScore, citation faithfulness, and hallucination rate. Integrate with RAGAS or TruLens.

- **User authentication and session persistence**: Add JWT-based authentication, per-user document namespaces, and conversation history storage (PostgreSQL or Supabase).

- **Citation graph integration**: Connect to Semantic Scholar or OpenAlex APIs to enrich paper metadata with citation counts, related works, and author information.

- **Automated literature review generation**: Generate structured literature review sections from multiple uploaded papers, highlighting agreements, contradictions, and research gaps.

- **Mobile-responsive UI**: Extend the frontend for full mobile usability with touch-friendly controls and responsive breakpoints.

---

# Chapter 7

## 7.1 Conclusion

This project demonstrates that a practical, production-quality AI research assistant can be built by combining modern frontend engineering with a focused Retrieval-Augmented Generation pipeline. The final system provides a premium conversational interface — with interactive particle animations, glassmorphic glassmorphism design, and smooth micro-animations — for interacting with one or more uploaded research papers, while grounding answers in retrieved and reranked document evidence and exposing those sources transparently.

From a **technical perspective**, the project integrates PDF processing, chunking, sentence-transformer embeddings, Qdrant persistent vector storage, BM25 + dense hybrid retrieval, neural cross-encoder reranking, streamed generation, multi-document comparison, PowerPoint generation, configurable model providers, source attribution, LangSmith tracing, 34+ automated tests, and cloud deployment into a coherent full-stack application.

From an **academic perspective**, it illustrates important engineering lessons about:

- Modular system design and separation of concerns
- The tradeoff between retrieval recall (bi-encoder) and ranking precision (cross-encoder)
- The complementary roles of dense embeddings and lexical scoring in hybrid retrieval
- Prompt construction for grounded generation versus hallucination reduction
- Observability and testing as first-class concerns in AI pipeline engineering
- UI/UX design choices that affect user trust and system adoption

From a **learning perspective**, the project required mastery of both frontend (Next.js, Tailwind, TypeScript, HTML5 Canvas animation) and backend (FastAPI, Python, vector databases, sentence-transformers, cross-encoders) development, retrieval system design, language model integration, asynchronous streaming, software testing, and cloud deployment. Most importantly, it demonstrated that reliable AI systems are not built by generation alone — they depend on careful retrieval, user experience design, transparency, and iterative refinement.

The Multimodal AI Research Assistant is a strong capstone outcome because it solves a real academic problem that every student and researcher faces, demonstrates full-stack implementation skill across multiple specialized domains, and provides a credible foundation for future research-grade or product-level extension.

---

# Chapter 8

## 8.1 References

1. Lewis, P., Perez, E., Piktus, A., et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.

2. Reimers, N., and Gurevych, I. *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP-IJCNLP, 2019.

3. Johnson, J., Douze, M., and Jégou, H. *Billion-scale similarity search with GPUs*. IEEE Transactions on Big Data, 2019. (FAISS)

4. Vaswani, A., Shazeer, N., Parmar, N., et al. *Attention Is All You Need*. NeurIPS, 2017.

5. Nogueira, R., and Cho, K. *Passage Re-ranking with BERT*. arXiv:1901.04085, 2019. (Cross-encoder reranking)

6. Robertson, S., and Zaragoza, H. *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in Information Retrieval, 2009.

7. Qdrant Team. *Qdrant Vector Database Documentation*. Available at: https://qdrant.tech/documentation/

8. FastAPI official documentation. Available at: https://fastapi.tiangolo.com/

9. Next.js official documentation. Available at: https://nextjs.org/docs

10. Tailwind CSS official documentation. Available at: https://tailwindcss.com/docs

11. OpenRouter Developer Documentation. Available at: https://openrouter.ai/docs/quickstart

12. Ollama API Documentation. Available at: https://docs.ollama.com/api/introduction

13. LangSmith Documentation. LangChain. Available at: https://docs.langchain.com/langsmith/home

14. Sentence-Transformers Documentation. Available at: https://www.sbert.net/

15. Hugging Face Cross-Encoder Models. Available at: https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2

16. python-pptx Documentation. Available at: https://python-pptx.readthedocs.io/
