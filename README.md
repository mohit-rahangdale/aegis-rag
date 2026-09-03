# AegisRAG

[![CI](https://github.com/mohit-rahangdale/aegis-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/mohit-rahangdale/aegis-rag/actions/workflows/ci.yml)

A production-ready Retrieval-Augmented Generation (RAG) service with hybrid search, multi-model fallback, safety guardrails, conversation memory, and automated evaluation.

## Architecture Overview

```text
User Query
    │
    ▼
FastAPI (/chat)
    │
    ▼
Guardrails & Fast-Path ──(greeting / routine dialogue)──► Instant Response (0 tokens)
    │                                                              ▲
    │ (substantive question)                                       │
    ▼                                                              │
Hybrid Retrieval (Qdrant Cloud dense + BM25 sparse)                │
    │                                                              │
    ▼                                                              │
Passage Reranker                                                   │
    │                                                              │
    ▼                                                              │
Relevance Check ──(weak context)──► Query Rewrite ──► Re-retrieve ─┘
    │
    ▼ (good context)
LLM Gateway (Gemini with Mistral failover + Circuit Breaker)
    │
    ▼
Grounding Verification & Output Guardrails (PII / Leak Redaction)
    │
    ▼
Memory Persistence (Redis sliding cache + PostgreSQL history)
    │
    ▼
Response to Client (Answer + Citations + Latency)
```

## Key Features

- **Multi-LLM Gateway**: Primary routing to Google Gemini with automatic failover to Mistral AI. Built-in exponential backoff retries, request timeouts, and circuit breaking.
- **Hybrid Retrieval**: Dense semantic vectors via Qdrant Cloud combined with sparse BM25 lexical search using Reciprocal Rank Fusion (RRF).
- **Corrective RAG (CRAG)**: LangGraph state machine that evaluates retrieved chunk relevance and rewrites queries when retrieved context is weak.
- **Token-Saving Guardrails**:
  - Intercepts and blocks adversarial prompt injections and jailbreaks.
  - Answers common conversational pleasantries (greetings, thanks, farewells) directly without LLM calls, saving tokens and latency.
- **Output Guardrails**: Redacts credentials/PII and blocks internal system prompt leaks before sending responses.
- **Hallucination Detection**: Verifies generated claims against retrieved passages to flag ungrounded output.
- **Two-Tier Memory**: Redis for fast recent-turn caching (sliding window) and PostgreSQL for durable conversation persistence and audits.
- **RAG Evaluation Harness**: Automated scoring of Recall@K, Context Precision, and Faithfulness against a golden benchmark dataset.
- **Automated CI/CD**: GitHub Actions pipeline validating linting, compilation, and unit tests across Python versions.

## API Endpoints

### Chat & Agent
- `POST /chat`: Run agentic RAG query with memory, citations, and grounding checks.
- `GET /conversations`: List active conversations with pagination.
- `GET /conversations/{id}`: Get complete conversation transcript.
- `DELETE /conversations/{id}`: Delete conversation from cache and database.

### Documents & Ingestion
- `POST /documents/upload`: Upload PDF, Markdown, or text file for indexing.
- `GET /documents`: List ingested documents.
- `GET /documents/{id}`: Get status and metadata of an ingested document.

### Retrieval
- `POST /retrieval/search`: Direct hybrid search (dense + sparse + rerank) over indexed chunks.

### Health
- `GET /health`: Health status of the API, PostgreSQL, Redis, MinIO, Qdrant, and LLM providers.

## Getting Started

### 1. Requirements
- Python 3.11+ (tested on Python 3.13)
- Docker & Docker Compose

### 2. Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/mohit-rahangdale/aegis-rag.git
cd aegis-rag
pip install -r requirements.txt
```

Copy the sample environment file:

```bash
cp .env.example .env
```

Configure your API keys in `.env`:
- `GEMINI_API_KEY`: Google AI Studio API key
- `MISTRAL_API_KEY`: Mistral AI API key (fallback provider)
- `QDRANT_URL` and `QDRANT_API_KEY`: Qdrant Cloud cluster endpoint and key

### 3. Start Supporting Services

Start PostgreSQL, Redis, and MinIO:

```bash
docker compose up -d
```

*(Note: Qdrant runs on Qdrant Cloud and does not need local container hosting).*

### 4. Run Migrations & Start Server

Apply database migrations:

```bash
alembic upgrade head
```

Start the application:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

## Testing & Evaluation

### 1. Run Automated Test Suite
```bash
pytest -v
```

### 2. Run RAG Evaluation Benchmark
Execute the automated evaluation harness against the golden benchmark dataset:

```bash
python -m app.evaluation.runner
```

This calculates and displays a terminal summary table measuring:
- **Recall@5**: Proportion of expected chunks retrieved in top 5.
- **Context Precision**: Rank-weighted precision of relevant passages.
- **Faithfulness**: Grounding ratio between generated answer and source context.
- **Average Latency**: End-to-end response time per turn.

### 3. Docker Build
Build and run the production container:

```bash
docker build -t aegisrag .
docker run -p 8000:8000 --env-file .env aegisrag
```

## Project Structure

```text
aegis-rag/
├── .github/workflows/ # GitHub Actions CI/CD pipelines
├── app/
│   ├── agent/         # LangGraph CRAG state machine and workflow nodes
│   ├── api/routes/    # FastAPI route handlers (chat, documents, retrieval, health)
│   ├── config/        # Pydantic settings and environment management
│   ├── core/          # Logging and middleware
│   ├── db/            # PostgreSQL models, repositories, and connection setup
│   ├── evaluation/    # RAG benchmark metrics (Recall@K, Precision, Faithfulness), runner
│   ├── gateway/       # Multi-LLM gateway (Gemini/Mistral, circuit breaker, retry)
│   ├── guardrails/    # Prompt injection defense, fast-path dialogue, output sanitization
│   ├── ingestion/     # File loaders (PDF, MD, TXT), text chunker, pipeline
│   ├── memory/        # Redis + PostgreSQL conversation memory manager
│   ├── retrieval/     # Dense (Qdrant), Sparse (BM25), Hybrid (RRF), Reranker
│   └── storage/       # Clients for PostgreSQL, Redis, MinIO, and Qdrant
├── alembic/           # Database migration versions
├── tests/             # Comprehensive unit, integration, and evaluation test suite
├── Dockerfile         # Multi-stage production container build
├── docker-compose.yml # PostgreSQL, Redis, MinIO services
├── requirements.txt   # Core Python dependencies
└── pyproject.toml     # Project metadata and tooling config
```
