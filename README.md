# Multimodal AI Research Assistant

A full-stack research assistant with a ChatGPT-style frontend and a FastAPI backend for PDF-grounded question answering using Retrieval-Augmented Generation (RAG).

## What It Does

The system lets a user:

- upload a research paper in PDF format
- ask natural-language questions about that paper
- retrieve relevant chunks from the indexed document
- generate grounded answers through an LLM provider
- view the retrieved source chunks used to support the answer

The current implementation is optimized for a strong single-user capstone demonstration and viva discussion.

## Report

Project report files generated for submission:

- `Multimodal AI Research Assistant using Retrieval-Augmented Generation (RAG) - Final Report.docx`
- `Multimodal AI Research Assistant using Retrieval-Augmented Generation (RAG) - Final Report.md`

## Tech Stack

Frontend:

- Next.js App Router
- React
- Tailwind CSS
- custom component-based chat UI
- markdown and code rendering support

Backend:

- FastAPI
- FAISS
- sentence-transformers
- httpx
- pypdf
- python-dotenv

LLM providers:

- OpenRouter by default
- Ollama optional

Observability and quality:

- LangSmith tracing
- pytest test suite
- retrieval accuracy check script

## Project Structure

```text
frontend/
  app/
    components/
    globals.css
    layout.tsx
    page.tsx
  lib/
backend/
  main.py
  pdf_utils.py
  rag_pipeline.py
  run_accuracy_check.py
  vector_store.py
  eval_cases.sample.json
  tests/
scripts/
package.json
README.md
```

## Features

- ChatGPT-like dark conversation UI
- dynamic greeting on first load
- sticky bottom input bar
- inline PDF upload from the composer
- multiple uploaded PDF documents per local session
- document query modes for current, selected, or all uploaded PDFs
- document-aware source citations with page numbers when available
- hybrid dense plus BM25 retrieval with configurable weights
- PDF extraction cleanup for ligatures, hyphenated line breaks, duplicate lines, page metadata, and extraction diagnostics
- retrieval evaluation reports with precision@k, recall@k, MRR, nDCG@k, and citation coverage
- streaming assistant responses
- thinking indicator and live streaming state
- markdown rendering
- styled code blocks with copy support
- collapsible source attribution section
- sidebar controls for provider, model, chunk size, and top-k
- identity handling for developer attribution
- reset controls for new chat and PDF clearing
- retrieval debug and retrieval evaluation endpoints
- backend test suite and retrieval accuracy runner

## Environment Files

Expected local environment files:

- `backend/.env`
- `frontend/.env.local`

Typical backend variables:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OLLAMA_BASE_URL=http://localhost:11434
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_PROJECT=capstone2draft2
```

Frontend uses:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Setup

### Frontend

```bash
cd frontend
npm install
```

### Backend

```bash
cd backend
py -3.13 -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
```

Backend dependencies include:

- `fastapi==0.115.12`
- `uvicorn[standard]==0.34.0`
- `faiss-cpu==1.12.0`
- `sentence-transformers==3.4.1`
- `langsmith==0.1.147`
- `pytest==8.4.1`

## Development Run

Run the full stack from the project root:

```bash
npm run dev
```

The root launcher:

- starts frontend and backend together
- uses the backend virtual environment directly
- auto-selects the first free local frontend and backend ports from a safe range
- prints the actual URLs it chose

If ports such as `3000` or `8000` are already occupied, the launcher will move to the next free port automatically.

## Core API

### `GET /`

Returns healthcheck information and vector store metadata.

### `GET /documents`

Returns the current backend document registry.

Each document includes:

- `document_id`
- `filename`
- `uploaded_at`
- `chunk_count`
- `source_type`
- `extraction` diagnostics such as total pages, extracted characters, empty pages, duplicate lines removed, and OCR status

### `POST /upload`

Uploads a PDF, extracts text, chunks the content, embeds it, and adds it to the vector store.

Multipart fields:

- `file`: PDF file
- `chunk_size`: optional integer, defaults to `700`

Returns the new `document_id`, document metadata, and the full current document list. Indexed chunks preserve `document_id`, `filename`, `page`, and `chunk_id` metadata. PDFs are normalized before chunking to repair common extraction artifacts such as `fi`/`fl` ligatures and hyphenated line breaks.

### `POST /chat`

Accepts a user query, message history, provider, model, top-k value, optional `document_ids`, and retrieval settings, then streams newline-delimited JSON events. Pass an empty `document_ids` array to search all uploaded documents, or pass one or more IDs to filter retrieval.

Retrieval settings:

- `dense_weight`: dense vector score weight, defaults to `0.72`
- `bm25_weight`: BM25 lexical score weight, defaults to `0.28`
- `candidate_pool_size`: dense/BM25 candidate pool before final ranking, defaults to `24`
- `rerank`: accepted for API compatibility, currently disabled

Stream event types:

- `{"type":"thinking"}`
- `{"type":"token","token":"..."}`
- `{"type":"sources","sources":[...]}`
- `{"type":"done"}`

### `POST /reset`

Supports scoped clearing:

- `{"mode":"chat"}` clears frontend chat state only and keeps indexed documents.
- `{"mode":"document","document_id":"..."}` deletes one indexed document.
- `{"mode":"all"}` clears all indexed PDF context.

### `POST /retrieval/debug`

Returns retrieved chunks and their scores for a given query.

Debug results include:

- final weighted score
- dense score
- BM25 score
- rerank score placeholder
- document and page metadata

### `POST /retrieval/evaluate`

Returns retrieval evaluation metrics such as:

- matched expected terms
- term recall
- hit status
- retrieved chunk payloads and scores
- precision@k
- recall@k
- MRR
- nDCG@k
- citation coverage

## Testing

Run the backend test suite:

```bash
cd backend
. .venv/Scripts/activate
pytest
```

Current automated coverage includes:

- FastAPI route tests with injected fake pipeline
- upload, reset, chat, and retrieval endpoint behavior
- retrieval evaluation logic
- PDF chunking utility behavior
- aggregate retrieval accuracy reporting

## Retrieval Accuracy Check

After uploading and indexing a PDF, run:

```bash
cd backend
. .venv/Scripts/activate
python run_accuracy_check.py --cases eval_cases.sample.json
```

This produces a report with:

- case count
- average term recall
- hit rate
- precision@k
- recall@k
- MRR
- nDCG@k
- citation coverage
- matched expected terms per case
- retrieved chunks and scores per case

You can also write the result to a file:

```bash
python run_accuracy_check.py --cases eval_cases.sample.json --output accuracy-report.json
```

You can also write a Markdown summary:

```bash
python run_accuracy_check.py --cases eval_cases.sample.json --output accuracy-report.json --markdown-output accuracy-report.md
```

## Current Design Notes

Important current design choices:

- custom RAG pipeline instead of LangChain orchestration
- local persisted FAISS storage
- multiple active PDF contexts in a local session-style document registry
- document-aware dense retrieval filters for current, selected, or all uploaded PDFs
- true BM25 lexical retrieval merged with dense FAISS retrieval
- PDF text normalization and extraction diagnostics before chunk indexing
- rerunnable JSON and Markdown retrieval evaluation reports
- chunk metadata backed by persisted FAISS records
- direct streaming from FastAPI to the frontend
- OpenRouter as default model provider with Ollama as fallback option

## Known Limitations

- local vector storage is process-local and partition-isolated by session ID. For high-volume enterprise production, a distributed vector database like Qdrant/Pinecone can be added, but for demo and viva purposes, session partitioning is fully sufficient and isolated.
- retrieval evaluation is still basic and term-based
- no advanced reranker yet, although the API and UI expose a disabled placeholder
- OCR is not enabled yet for scanned/image-only PDFs
- PDF extraction quality can affect retrieval precision
- not yet a full multimodal figure/table reasoning system

## Recommended Next Improvements

- distributed vector database (e.g. Qdrant or Pinecone) for multi-node deployments
- reranking models (e.g. Cohere Rerank or BGE Reranker)
- OCR support for scanned/image-only PDFs
- answer-quality evaluation beyond retrieval recall
- LangGraph-style advanced orchestration if the workflow becomes agentic

## Deployment

Recommended deployment split for a free preview setup:

- Frontend: Vercel
- Backend: Render Free Web Service

This is the best free deployment option for the current codebase.

### Why Render is the right backend choice here

- FastAPI runs cleanly on Render web services.
- The current backend is not a good fit for Vercel serverless because it uses `sentence-transformers`, `torch`, and local vector storage.
- Render is simpler than trying to force this backend into a serverless function model.

### Render backend deployment (click-by-click)

Official reference:

- https://render.com/docs/deploy-fastapi

This repo includes `render.yaml`, but you can also configure the service manually through the Render dashboard.

#### Step 1: Open Render

- Sign in to Render.
- Click `New +`.
- Click `Web Service`.
- Choose `Build and deploy from a Git repository`.

#### Step 2: Connect GitHub

- Connect your GitHub account if Render asks.
- Select this repository:
  `Swetankan/Multimodal-AI-Research-Assistant`

#### Step 3: Configure the backend service

Use these settings:

- Name: `multimodal-ai-research-assistant-api`
- Root Directory: `backend`
- Runtime: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Instance Type: `Free`

#### Step 4: Add backend environment variables

Add these in the Render dashboard:

- `OPENROUTER_API_KEY=your_key_here`
- `OPENROUTER_MODEL=openai/gpt-4o-mini`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- `OPENROUTER_SITE_URL=https://your-frontend-url.vercel.app`
- `OPENROUTER_APP_NAME=Multimodal AI Research Assistant`
- `FRONTEND_ORIGINS=https://your-frontend-url.vercel.app`
- `LANGSMITH_TRACING=true`
- `LANGSMITH_ENDPOINT=https://api.smith.langchain.com`
- `LANGSMITH_API_KEY=your_langsmith_key_here`
- `LANGSMITH_PROJECT=capstone2draft2`

Optional only if you want Ollama instead of OpenRouter:

- `OLLAMA_BASE_URL=http://localhost:11434`

#### Step 5: Deploy the backend

- Click `Create Web Service`.
- Wait for the deployment to finish.
- Open the generated Render URL.
- Visit `/` on that URL to confirm the healthcheck responds.

Example:

- `https://multimodal-ai-research-assistant-api.onrender.com/`

### Vercel frontend deployment (click-by-click)

Official references:

- https://vercel.com/docs/frameworks/full-stack/nextjs
- https://vercel.com/docs/git/vercel-for-github

#### Step 1: Open Vercel

- Sign in to Vercel.
- Click `Add New...`.
- Click `Project`.
- Import your GitHub repository:
  `Swetankan/Multimodal-AI-Research-Assistant`

#### Step 2: Configure the frontend project

Use these settings:

- Framework Preset: `Next.js`
- Root Directory: `frontend`
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: leave default for Next.js

#### Step 3: Add frontend environment variable

Set:

- `NEXT_PUBLIC_API_BASE_URL=https://your-render-backend.onrender.com`

#### Step 4: Deploy the frontend

- Click `Deploy`.
- Wait for the deployment to finish.
- Open the Vercel URL.

### Final post-deployment update

After Vercel gives you the real frontend URL, go back to Render and confirm these values are correct:

- `OPENROUTER_SITE_URL=https://your-real-vercel-url.vercel.app`
- `FRONTEND_ORIGINS=https://your-real-vercel-url.vercel.app`

Then redeploy the backend once so the updated values are active.

### Preview mode

- Vercel automatically creates preview deployments for future pushes and pull requests.
- The backend already allows `*.vercel.app` through CORS, so those preview frontends can call the Render backend.

### Important limitation of free hosting

Render free services can sleep when idle, and this backend stores indexed document state locally. That means free deployment is suitable for preview/demo use, but uploaded PDFs and indexed vectors should be treated as temporary deployment state.

## Deployment Troubleshooting

- If Render fails with a aiss-cpu version resolution error, redeploy after pulling the latest commit where FAISS is pinned to 1.12.0.
- If Vercel shows 404 NOT_FOUND, open the Vercel project settings and confirm Root Directory is set to rontend. The frontend must not be deployed from the repository root.


## Hosted Runtime Notes

- On free Render instances, the first PDF upload can still be slow because the embedding model must load on the backend instance.
- The backend now supports MODEL_TIMEOUT_SECONDS to prevent chat requests from hanging forever when the upstream model provider stalls.
- For hosted deployments, prefer EMBEDDING_MODEL=sentence-transformers/paraphrase-MiniLM-L3-v2 unless you specifically want the larger L6 model.
