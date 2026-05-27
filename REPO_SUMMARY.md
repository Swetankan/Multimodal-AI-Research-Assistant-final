# Multimodal AI Research Assistant — Repository Summary

> **A full-stack, document-grounded AI research companion.** Upload a research paper, ask questions in natural language, and receive streamed answers backed by retrieved evidence — not hallucinations.

---

## What This Project Does

Most AI chatbots answer from training memory, not from your actual document. This assistant is different:

1. You **upload a PDF** research paper
2. It **chunks + embeds** the document into a local vector store
3. When you ask a question, it **retrieves the most relevant chunks** using hybrid BM25 + dense search
4. Those chunks are **reranked by a cross-encoder** for precision
5. The retrieved evidence is **injected into the LLM prompt** to generate a grounded answer
6. The **answer streams live** with a collapsible Sources panel showing exactly which chunks were used

This is Retrieval-Augmented Generation (RAG) — answers you can verify, not just trust.

---

## Who It's For

- **Students** reviewing papers for assignments or exams
- **Researchers** doing literature review or comparing methodologies
- **Capstone / thesis students** who need to deeply understand and present papers
- **Developers** exploring RAG system design in a clean, production-quality codebase

---

## Quick Start (Run Locally)

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [OpenRouter API key](https://openrouter.ai)

### 1 — Clone the repo
```bash
git clone https://github.com/Swetankan/Multimodal-AI-Research-Assistant-final.git
cd Multimodal-AI-Research-Assistant-final
```

### 2 — Start the Backend
```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Edit .env and set OPENROUTER_API_KEY=sk-or-...

# Start server
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```
Backend runs at → **http://localhost:8001**

### 3 — Start the Frontend
```bash
cd frontend

# Install dependencies
npm install

# Create env file
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8001" > .env.local

# Start dev server
npm run dev
```
Frontend runs at → **http://localhost:3000**

### 4 — Use the App
1. Open **http://localhost:3000**
2. Click **+** → upload a PDF research paper
3. Ask a question in the chat
4. See the streamed answer + Sources panel

---

## Features

### Core RAG Features
| Feature | Description |
|---|---|
| **PDF Upload & Ingestion** | Upload up to 15MB PDFs. Backend extracts, chunks (configurable 300–1200 tokens), embeds, and indexes instantly |
| **Hybrid Retrieval** | BM25 lexical scoring + dense cosine similarity fused with configurable weights (default 72% dense / 28% BM25) |
| **Neural Reranking** | Optional cross-encoder (`ms-marco-MiniLM-L-6-v2`) reranks retrieved chunks for higher precision |
| **Streaming Answers** | Token-by-token SSE streaming for live typing effect — no waiting for full response |
| **Source Attribution** | Every answer shows collapsible Sources panel with exact text chunks + page numbers used |
| **Multi-Document** | Upload multiple PDFs, select which to query from (Current / Selected / All) |

### Advanced Features
| Feature | Description |
|---|---|
| **Paper Comparison** | Select 2+ documents → structured comparison table across method, dataset, metrics, limitations |
| **PPT Generation** | Auto-generate a downloadable 16:9 PowerPoint deck from indexed document content |
| **Retrieval Debug** | Inspect raw retrieval scores (dense + BM25 + rerank) for any query |
| **Retrieval Evaluation** | Compute term-recall and hit-rate metrics on demand |
| **Multi-Provider LLM** | OpenRouter (GPT-4o mini, Claude 3.5, Gemini 2.0, Llama 3.1) or Ollama (local) |
| **Session Isolation** | Each browser session gets isolated storage via `X-Session-ID` header |
| **LangSmith Tracing** | Full pipeline observability: ingestion, retrieval, reranking, generation all traced |

### UI/UX Features
| Feature | Description |
|---|---|
| **Particle Background** | Custom HTML5 Canvas neural-constellation animation with mouse-repulsion physics |
| **Glassmorphic Sidebar** | Smooth opacity+translate collapse animation, emerald range sliders, backdrop blur |
| **Gradient Hero Text** | Green→violet animated gradient heading text |
| **Markdown Rendering** | Full GFM: tables, headings, bold, italic, lists, blockquotes |
| **Code Blocks** | Syntax-highlighted with copy button |
| **Thinking Indicator** | Animated dots while retrieval + LLM generation is in progress |

---

## Repository Structure

```
capstone2draft2/
│
├── backend/                   ← Python FastAPI backend
│   ├── main.py                  All 9 API endpoints + CORS + session routing
│   ├── rag_pipeline.py          Core RAG: ingest, retrieve, rerank, stream, compare, PPT
│   ├── vector_store.py          FAISS hybrid vector store (lazy ML imports)
│   ├── qdrant_store.py          Qdrant persistent vector store (alternative)
│   ├── pdf_utils.py             PDF extraction + overlap chunking
│   ├── ppt_utils.py             PowerPoint deck generation
│   ├── requirements.txt         All Python dependencies
│   ├── .env.example             Template for all environment variables
│   ├── railway.toml             Railway.app deployment config
│   ├── pytest.ini               Test runner config
│   ├── verify_production.py     Pre-deploy verification script
│   ├── run_accuracy_check.py    Retrieval accuracy benchmark
│   ├── eval_cases.sample.json   Sample evaluation test cases
│   └── tests/                   34 automated pytest tests
│       ├── test_ingestion.py
│       ├── test_retrieval.py
│       ├── test_reranking.py
│       ├── test_compare.py
│       └── test_api.py
│
├── frontend/                  ← Next.js 15 TypeScript frontend
│   ├── app/
│   │   ├── layout.tsx           Root layout (Manrope + IBM Plex Mono fonts)
│   │   ├── page.tsx             Entry point
│   │   ├── globals.css          CSS variables, gradients, slider styles
│   │   └── components/
│   │       ├── ChatWindow.tsx        Main state + streaming orchestrator
│   │       ├── Sidebar.tsx           Settings panel + document manager
│   │       ├── InputBar.tsx          Message composer + PDF upload
│   │       ├── MessageBubble.tsx     Chat message (markdown + sources)
│   │       ├── MarkdownRenderer.tsx  react-markdown + GFM
│   │       ├── CodeBlock.tsx         Syntax highlight + copy
│   │       └── ParticlesBackground.tsx  Canvas particle animation
│   ├── lib/
│   │   ├── api.ts               All backend API calls (typed)
│   │   └── utils.ts             Tailwind class merger utility
│   ├── tailwind.config.ts       Custom theme tokens
│   ├── next.config.ts           Next.js config
│   └── .env.local               NEXT_PUBLIC_API_BASE_URL
│
├── render.yaml                ← Render.com deployment config (backend)
├── ARCHITECTURE.md            ← Technical architecture deep-dive
├── REPO_SUMMARY.md            ← This file
├── Final_Report_Capstone_II_Group77.md    Capstone report (markdown)
├── Final_Report_Capstone_II_Group77.docx  Capstone report (Word)
└── README.md                  ← Project readme
```

---

## Tech Stack

### Backend
| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115 | Web framework + streaming responses |
| `uvicorn` | 0.34 | ASGI server |
| `pypdf` | 5.4 | PDF text extraction |
| `sentence-transformers` | 3.4 | Semantic embeddings (`all-MiniLM-L6-v2`) |
| `faiss-cpu` | 1.12 | Vector similarity search |
| `qdrant-client` | 1.13 | Persistent vector database |
| `httpx` | 0.28 | Async HTTP client (LLM API calls) |
| `langsmith` | 0.1 | Pipeline observability + tracing |
| `python-pptx` | 1.0 | PowerPoint generation |
| `python-dotenv` | 1.0 | Environment variable loading |
| `pytest` | 8.4 | Test runner |

### Frontend
| Package | Version | Purpose |
|---|---|---|
| `next` | 15.3 | React framework (App Router) |
| `react` | 19 | UI library |
| `tailwindcss` | 3.4 | Utility-first CSS |
| `react-markdown` | 10 | Markdown rendering |
| `remark-gfm` | 4 | GitHub Flavored Markdown |
| `react-syntax-highlighter` | 16 | Code block syntax highlighting |
| `lucide-react` | 0.511 | Icon library |
| `clsx` + `tailwind-merge` | — | Dynamic class composition |

---

## Key Design Decisions

### 1. Custom RAG, Not LangChain
The pipeline is linear: ingest → chunk → embed → retrieve → rerank → prompt → stream. Building it from scratch keeps every stage visible and debuggable. No hidden abstractions — great for academic viva and future modification.

### 2. Lazy ML Import Strategy
```python
# PyTorch + faiss load only when first PDF is uploaded, NOT at server start
def _get_encoder(self):
    from sentence_transformers import SentenceTransformer  # lazy
    ...
```
This keeps startup RAM under 100MB, critical for Render's 512MB free-tier limit.

### 3. Hybrid Retrieval (Dense + BM25)
Pure dense search misses exact method names and acronyms. BM25 lexical scoring fills this gap. The 72/28 default blend is tuned for research paper queries and is configurable by the user.

### 4. Cross-Encoder as Second Pass
Dense bi-encoders compare query and chunk independently — fast but imprecise. The cross-encoder reads query+chunk together, producing much better relevance judgement. Running it only on the top-24 candidates (not all chunks) keeps latency manageable on CPU.

### 5. FAISS + Qdrant Dual Support
`VECTOR_DB_PROVIDER=faiss` (default): simple file-based, no service required, great for local and demo.
`VECTOR_DB_PROVIDER=qdrant`: persistent across restarts, supports larger collections, better for staging/prod.

### 6. Session-Based Pipeline Isolation
Each `X-Session-ID` header gets its own `ResearchAssistantPipeline` with isolated FAISS storage. Multiple users can use the app simultaneously without sharing document state.

### 7. Direct SSE Streaming
No buffering — tokens stream directly from OpenRouter → FastAPI → browser. This gives live typing UX and means the browser shows partial answers even for slow connections.

---

## Deployment

| Service | Platform | Plan | URL |
|---|---|---|---|
| Backend (FastAPI) | [Render.com](https://render.com) | Free | `https://*.onrender.com` |
| Frontend (Next.js) | [Vercel](https://vercel.com) | Free | `https://*.vercel.app` |
| Code | [GitHub](https://github.com/Swetankan/Multimodal-AI-Research-Assistant-final) | Public | — |

Auto-deploys on every `git push` to `main`.

> ⚠️ **Render free tier cold starts**: spins down after 15 min idle; first request takes ~30–60s to wake up.

---

## Limitations

| Limitation | Notes |
|---|---|
| Single PDF per session (current) | Multi-doc supported but isolated per session |
| Ephemeral FAISS on Render free | Disk resets on restart; upgrade plan or use Qdrant Cloud for persistence |
| CPU-bound reranking | Acceptable for demo; GPU or hosted reranking API needed for high traffic |
| Text-only grounding | Figures, charts, and embedded images are not parsed |
| No auth / rate limiting | Suitable for demo; needs JWT + rate limits for public production |
| 15MB PDF limit | Configurable via `MAX_UPLOAD_BYTES` env var |

---

## Automated Testing

```bash
cd backend
pytest tests/ -v
```

34 tests across 5 modules. All pass on current codebase.

| Module | Tests |
|---|---|
| `test_ingestion.py` | PDF upload, chunking, metadata |
| `test_retrieval.py` | FAISS search, BM25, hybrid fusion |
| `test_reranking.py` | Cross-encoder score ordering |
| `test_compare.py` | Multi-doc comparison pipeline |
| `test_api.py` | Endpoint status codes, SSE format |

---

## References

- [RAG paper — Lewis et al., NeurIPS 2020](https://arxiv.org/abs/2005.11401)
- [Sentence-BERT — Reimers & Gurevych, EMNLP 2019](https://arxiv.org/abs/1908.10084)
- [FAISS — Johnson et al., IEEE 2019](https://arxiv.org/abs/1702.08734)
- [Cross-encoder reranking — Nogueira & Cho, 2019](https://arxiv.org/abs/1901.04085)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [OpenRouter API](https://openrouter.ai/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
