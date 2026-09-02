# AegisRAG — System Architecture & Decisions

## 1. Executive Summary & Purpose

AegisRAG is a production-grade Corrective Retrieval-Augmented Generation (CRAG) and Agentic AI platform designed to demonstrate modern enterprise GenAI engineering practices. It replaces naive chatbot architectures with a reliable, observable, self-correcting, and strictly guarded system.

---

## 2. Core Architectural Principles

1. **Production-Minded Engineering**: Modular Python architecture, strict typing with Pydantic, dependency injection, resilience patterns (circuit breakers, exponential backoffs, multi-LLM failovers), and comprehensive automated testing.
2. **Pragmatic Complexity (No Overengineering)**: Avoid distributed system bloat (no unnecessary Kubernetes, Kafka, or complex multi-agent swarms). The entire application remains deployable, understandable, and testable by a single engineer.
3. **Defense in Depth**: Guardrails at input (prompt injection detection, topic boundaries), retrieval (confidence scoring, relevance verification), generation (grounding checks, citation verification), and output (hallucination defense).
4. **Architectural Traceability**: Every architectural decision is documented with trade-offs, alternatives considered, and rationale.

---

## 3. Target End-to-End Architecture

```text
                                 [ Client / API Request ]
                                             │
                                             ▼
                                     FastAPI Application
                                             │
                                             ▼
                                  Request Validation (Pydantic)
                                             │
                                             ▼
                                   Agentic Orchestrator
                                       (LangGraph)
                                             │
                        ┌────────────────────┼────────────────────┐
                        ▼                    ▼                    ▼
                 Input Guardrails    Conversation Memory    Query Analysis
              (NeMo / Injection DB)     (Redis/PG)        (Intent / Subqueries)
                        │                    │                    │
                        └────────────────────┼────────────────────┘
                                             ▼
                                    Hybrid Retrieval Layer
                                             │
                                 ┌───────────┴───────────┐
                                 ▼                       ▼
                           Dense Search            Sparse Search
                          (Qdrant Cloud)              (BM25)
                                 │                       │
                                 └───────────┬───────────┘
                                             ▼
                                     Reciprocal Rank Fusion
                                             │
                                             ▼
                                      Neural Reranker
                                             │
                                             ▼
                                 Retrieval Quality Gate
                                             │
                             ┌───────────────┴───────────────┐
                             ▼ (Quality >= Threshold)        ▼ (Quality < Threshold)
                         Accept Chunks                 Query Rewrite & Re-retrieval
                             │                               (Max 2 iterations)
                             └───────────────┬───────────────┘
                                             ▼
                                    Multi-LLM Gateway
                                             │
                                 ┌───────────┴───────────┐
                                 ▼ (Primary)             ▼ (Fallback)
                              Gemini                   Mistral
                                 │                       │
                                 └───────────┬───────────┘
                                             ▼
                                  Grounding & Citation Check
                                             │
                                             ▼
                                      Output Guardrails
                                             │
                                             ▼
                                    Validated Response
                                             │
                         ┌───────────────────┼───────────────────┐
                         ▼                   ▼                   ▼
                     PostgreSQL            Redis            Langfuse / MLflow
                  (Long-term store)     (Short cache)     (Observability/Metrics)
```

---

## 4. Phase 1 Architecture Decisions & Rationales

### 4.1 Web Framework: FastAPI

* **Problem Solved**: High-performance asynchronous REST API interface with automatic OpenAPI / Swagger documentation and native Pydantic validation.
* **Alternatives Considered**:
  * *Flask*: Mature and lightweight, but lacks native asynchronous request handling without greenlets/gevent, requires external plugins for schema validation, and has no native OpenAPI generation.
  * *Django / Django Ninja*: Heavyweight, introduces complex ORM abstractions and boilerplate unnecessary for an AI gateway/agent service.
* **Decision**: **FastAPI** provides native async/await for non-blocking I/O (critical for streaming LLM responses and parallel vector/lexical retrieval), automatic documentation, and native Pydantic v2 performance.

### 4.2 Configuration: Pydantic Settings

* **Problem Solved**: Type-safe application configuration, automatic environment variable parsing, casing normalization, and `.env` support.
* **Alternatives Considered**:
  * *Standard `os.environ`*: Fragile, untyped, provides no default values or validation at startup.
  * *Dynaconf*: Powerful but adds external dependencies with complex multi-format hierarchies when standard Pydantic models already exist throughout the app.
* **Decision**: **Pydantic Settings** (`pydantic-settings`) leverages existing Pydantic validation knowledge, guarantees fail-fast configuration on invalid types at startup, and provides cached singleton access via `@lru_cache`.

### 4.3 Structured Logging: JSON & Standard Stream Formatter

* **Problem Solved**: Standardized log emission capable of machine parsing by log collectors (Datadog, CloudWatch, Loki) in production while retaining human-readable text output for local development.
* **Alternatives Considered**:
  * *Standard `print()`*: Unacceptable for production; no log levels, timestamps, or routing.
  * *Loguru*: Clean API but introduces non-standard handler abstractions that complicate integrations with ASGI servers and standard Python logging hooks.
* **Decision**: Custom `JSONFormatter` built on Python's native `logging` library. Emits ISO 8601 UTC timestamps, service name, log levels, file locations, request IDs, and arbitrary extra fields without third-party vendor lock-in.

### 4.4 Testing Framework: Pytest + HTTPX

* **Problem Solved**: Testing both synchronous and asynchronous endpoints with reusable fixtures and fast execution.
* **Alternatives Considered**:
  * *Standard `unittest`*: Verbose boilerplate, less expressive fixtures, difficult async test setups.
* **Decision**: **Pytest** with `pytest-asyncio` and `httpx.AsyncClient` + `TestClient`.

---

## 5. Technology Matrix

| Component | Technology Selected | Primary Purpose |
| :--- | :--- | :--- |
| **API Framework** | FastAPI | High-throughput asynchronous HTTP routing & OpenAPI |
| **Config & Validation** | Pydantic v2 / Pydantic Settings | Type-safe data validation and configuration |
| **Primary LLM** | Google Gemini (via Gateway) | Cost-effective, high-context reasoning |
| **Fallback LLM** | Mistral (via Gateway) | High-reliability failover when primary degrades |
| **Vector DB** | Qdrant Cloud | Dense vector similarity indexing and payload filtering |
| **Lexical Retrieval** | BM25 / Sparse Index | Exact keyword and code/symbol matching |
| **Database** | PostgreSQL + SQLAlchemy + Alembic | Relational document metadata, audit logs, long-term memory |
| **Cache & State** | Redis | Session state, short-term message memory, circuit breakers |
| **Object Storage** | MinIO (S3-compatible) | Raw file storage (PDF, Markdown, TXT) |
| **Agentic Workflow** | LangGraph | Deterministic state machine for Corrective RAG |
| **Guardrails** | NeMo Guardrails + Custom Pydantic | Defense against prompt injection, jailbreaks, hallucinations |
| **Experiment Tracking** | MLflow | Retrieval parameter tuning, prompt evaluations, metric logging |
| **Data Versioning** | DVC | Versioning gold evaluation benchmarks and test datasets |
| **Observability** | Langfuse | Distributed LLM tracing, latency, token, and cost tracking |
| **CI/CD** | GitHub Actions | Automated linting, test suites, and evaluation metric gates |
