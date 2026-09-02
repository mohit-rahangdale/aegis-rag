# AegisRAG

> Production-oriented Corrective RAG and Agentic AI platform with multi-LLM failover, hybrid retrieval, reranking, AI guardrails, memory, evaluation, observability, and LLMOps.

---

## 🎯 Overview

**AegisRAG** is an enterprise-grade GenAI engineering platform built to solve the real-world limitations of naive Retrieval-Augmented Generation (RAG) and fragile chatbot toys.

Instead of assuming retrieved chunks are always accurate, AegisRAG evaluates retrieval quality dynamically, rewrites ambiguous queries, executes iterative re-retrieval (CRAG), and enforces strict grounding before answering. A resilient **Multi-LLM Gateway** provides automatic fallback from Gemini to Mistral with exponential backoff and circuit breaking, while multi-layered guardrails protect against prompt injection and toxic outputs.

---

## 🏛️ System Architecture

```text
                                 [ User / Client Query ]
                                            │
                                            ▼
                                   FastAPI Application
                                            │
                                            ▼
                                Pydantic Request Validation
                                            │
                                            ▼
                                  Agentic Orchestrator
                                      (LangGraph)
                                            │
                        ┌───────────────────┼───────────────────┐
                        ▼                   ▼                   ▼
                 Input Guardrails         Memory          Query Analysis
               (Prompt Injection DB)    (Redis/PG)       (Intent/Subqueries)
                        │                   │                   │
                        └───────────────────┼───────────────────┘
                                            ▼
                                  Hybrid Retrieval Layer
                                            │
                                 ┌──────────┴──────────┐
                                 ▼                     ▼
                           Dense Search          Sparse Search
                          (Qdrant Cloud)            (BM25)
                                 │                     │
                                 └──────────┬──────────┘
                                            ▼
                                      Neural Reranker
                                            │
                                            ▼
                                Retrieval Quality Gate (CRAG)
                                            │
                             ┌──────────────┴──────────────┐
                             ▼                             ▼
                        Good Context                  Poor Context
                             │                             │
                             │                       Query Rewrite
                             │                             │
                             │                        Re-retrieval
                             │                             │
                             └──────────────┬──────────────┘
                                            ▼
                                    Multi-LLM Gateway
                                 ┌─────────────────────┐
                                 │ Gemini (Primary)    │
                                 │      ↓ fallback     │
                                 │ Mistral             │
                                 └─────────────────────┘
                                            │
                                            ▼
                                 Grounding & Citation Check
                                            │
                                            ▼
                                    Output Guardrails
                                            │
                                            ▼
                                   Validated Answer
                                            │
                        ┌───────────────────┼───────────────────┐
                        ▼                   ▼                   ▼
                    PostgreSQL            Redis              Langfuse
                 (Metadata & Memory)   (Session Cache)     (Observability)
```

---

## 🛠️ Feature & Technology Mapping

| Feature | Technology | Engineering Purpose |
| :--- | :--- | :--- |
| **Multi-LLM Gateway** | Gemini + Mistral | Resilient failover, circuit breaking, retry & cost tracking |
| **Hybrid Retrieval** | Qdrant Cloud + BM25 | Dense semantic search + lexical exact matching |
| **Neural Reranking** | Cross-Encoder Reranker | Precision scoring for top candidates before generation |
| **Corrective RAG** | LangGraph State Graph | Self-correction loop: evaluates retrieval and rewrites query |
| **Grounding Check** | Hallucination Detector | Verifies response faithfulness against retrieved context |
| **AI Guardrails** | NeMo Guardrails + Pydantic | Defense against prompt injection, jailbreaks, and toxic output |
| **Conversation Memory** | Redis + PostgreSQL | Short-term cache + durable conversation context |
| **RAG Evaluation** | RAGAS / DeepEval | Measures Recall@K, Context Precision, and Faithfulness |
| **LLM Evaluation** | Custom Eval Framework | Measures instruction adherence, latency, tokens, and cost |
| **Experiment Tracking** | MLflow | Compares chunk sizes, embeddings, rerankers, and prompts |
| **Data Versioning** | DVC | Version-controls golden benchmarks and evaluation datasets |
| **Drift Monitoring** | Evidently AI | Tracks query drift, retrieval scores, and fallback rates |
| **Observability** | Langfuse | Distributed end-to-end tracing for every LLM and retrieval call |
| **CI/CD Automation** | GitHub Actions | Automated linting, test suite, and evaluation regression gates |

---

## 🚀 Quick Start (Phase 1)

### 1. Prerequisites

- Python 3.11+ (Python 3.13 tested)
- Git

### 2. Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/aegis-rag.git
cd aegis-rag

# Copy environment settings
cp .env.example .env

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Interactive API Documentation

Open your browser to:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Testing & Validation

Execute the test suite with `pytest`:

```bash
pytest -v
```

Execute Python bytecode compilation check:

```bash
python -m compileall app
```

---

## 🗺️ Project Roadmap & Status

- [x] **Phase 1: Foundation** (FastAPI, Pydantic Settings, Structured Logging, Health, Tests, Docs)
- [ ] **Phase 2: Production LLM Gateway** (Gemini + Mistral fallback, circuit breaker, retry, usage tracking)
- [ ] **Phase 3: Data & Storage** (PostgreSQL, Qdrant Cloud, Redis, MinIO)
- [ ] **Phase 4: Document Ingestion Pipeline** (PDF/TXT/MD, chunking, embeddings, checksums)
- [ ] **Phase 5: Hybrid Retrieval & Reranking** (Dense + Sparse fusion, reranker)
- [ ] **Phase 6: Corrective RAG Workflow** (Retrieval evaluation, query rewriting, grounding check)
- [ ] **Phase 7: Agentic Orchestration** (LangGraph state machine)
- [ ] **Phase 8: AI Guardrails & Prompt Injection Defense** (NeMo Guardrails, multi-layer validation)
- [ ] **Phase 9: Conversation Memory** (Redis short-term + Postgres long-term)
- [ ] **Phase 10: Multi-layer Evaluation** (LLM, RAG, and Application evaluation benchmarks)
- [ ] **Phase 11: MLOps & LLMOps** (DVC, MLflow experiment tracking, Evidently drift)
- [ ] **Phase 12: Observability & Tracing** (Langfuse distributed tracing)
- [ ] **Phase 13: CI/CD & Evaluation Gates** (GitHub Actions automated pipeline)
- [ ] **Phase 14: Docker & Deployment** (Production Dockerfile, docker-compose)
- [ ] **Phase 15: Final Hardening & Audit** (Security audit, performance verification)
