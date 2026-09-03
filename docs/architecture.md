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
              (Injection & Fast-Path)    (Redis/PG)        (Intent / Subqueries)
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

### 4.5 Production LLM Gateway Architecture

* **Problem Solved**: Single-provider fragility, vendor lock-in, unhandled transient errors, rate limits, and cascading downstream failures when external LLM endpoints degrade.
* **Key Design Decisions**:
  1. **Interface Segregation via `LLMProvider`**:
     * Concrete providers (`GeminiProvider`, `MistralProvider`) are purely responsible for payload translation and client invocation.
     * Crucially, providers DO NOT implement their own retry, timeout, or circuit breaking loops.
  2. **Centralized Gateway Resilience**:
     * `LLMGateway` centralizes exponential backoff with jitter, timeout bounds, and per-provider circuit breakers (`CLOSED` -> `OPEN` -> `HALF_OPEN`).
     * Prevents duplicate retry logic and ensures consistent observability across all model calls.
  3. **Automatic Failover Routing**:
     * When Gemini fails or its circuit breaker is OPEN, the gateway immediately fails over to Mistral without failing the upstream client request.
  4. **Financial and Usage Accounting**:
     * Every call calculates token consumption (`prompt_tokens`, `completion_tokens`) and estimated financial cost in USD via model rate tables.
  5. **Traceable Request Correlation**:
     * `request_id` is propagated end-to-end and injected into structured logs for auditability.

### 4.6 Data and Storage Architecture

* **Problem Solved**: Heterogeneous storage demands in a production RAG system (relational metadata, temporary caching, raw file storage, and dense vector embeddings).
* **Key Design Decisions**:
  1. **PostgreSQL with SQLAlchemy & Alembic**:
     * Stores relational document records, SHA-256 checksums (for ingestion deduplication), processing states, and timestamps.
     * Async SQLAlchemy with `asyncpg` enables non-blocking query execution.
  2. **Redis**:
     * Ultra-low latency in-memory store for conversation state, short-term message buffers, and fast session coordination.
  3. **MinIO (S3-Compatible Object Store)**:
     * Stores immutable raw files (PDFs, Markdown, text files) prior to chunking and extraction.
     * Prevents large binary payloads from bloating PostgreSQL.
  4. **Qdrant Cloud (Managed Vector Engine)**:
     * Hosted vector search engine isolated from local infrastructure bloat.
     * Implements HNSW indexing and payload filtering for dense retrieval.
  5. **Unified Health Probing Without Credential Leakage**:
     * Parallel non-blocking health checks report dependency statuses without exposing database connection strings or secret keys.

### 4.7 Ingestion, Hybrid Retrieval & Reranking Architecture

* **Problem Solved**: Single-retriever blindness (dense vectors missing exact acronyms/codes, keyword search missing semantic intent) and noisy context drowning the LLM generator.
* **Key Design Decisions**:
  1. **Multi-Format Ingestion**:
     * Dedicated loaders for PDF (`pypdf`), Markdown, and plain text with page-aware extraction.
     * Content deduplication via SHA-256 prevents re-embedding existing documents.
  2. **Boundary-Preserving Chunking**:
     * `TextChunker` groups text along natural paragraph and sentence boundaries with configurable overlap windows.
  3. **Hybrid Dense + Sparse Search**:
     * **Dense**: Qdrant cosine similarity search over Gemini vector embeddings.
     * **Sparse**: BM25 keyword matching for exact terms, acronyms, and technical IDs.
     * **Fusion**: Reciprocal Rank Fusion (RRF) normalizes and fuses ranked lists using $RRF(d) = \sum \frac{w}{60 + rank}$.
  4. **Contextual Passage Reranking**:
     * Post-retrieval cross-scoring elevates the most precise passages to top positions before passing to generation.

### 4.8 Corrective Agentic RAG (CRAG), Guardrails & Memory Architecture

* **Problem Solved**: Susceptibility to adversarial prompt injection, hallucinated answers unsupported by context, static retrieval failures, and stateless forgetfulness across turns.
* **Key Design Decisions**:
  1. **Deterministic Agentic Orchestration via LangGraph**:
     * A `StateGraph` defines the explicit control flow: `Guardrail -> Retrieve -> Grade -> (Rewrite if weak) -> Generate -> Verify Grounding -> Memory Persistence`.
     * Replaces opaque black-box loops with observable, auditable transitions.
  2. **Automated Retrieval Correction (CRAG)**:
     * Chunks below confidence floor trigger query reformulation via the LLM gateway.
     * Prevents poor search results from polluting the generation prompt, bounded by an iteration budget (max 2 iterations).
  3. **Multi-Layer Safety Guardrails**:
     * **Input Stage**: Pattern and heuristic defense against system prompt leaks, instruction overrides, and jailbreak personas (e.g. DAN).
     * **Output Stage**: Factual grounding check measuring lexical and semantic alignment between retrieved context passages and the generated claims to flag hallucinations.
  4. **Multi-Tier Hybrid Conversation Memory**:
     * **Short-Term Tier**: Redis key-value cache (`memory:conv:{id}`) storing recent turns with sliding TTL for ultra-low latency prompt augmentation.
     * **Long-Term Tier**: PostgreSQL `conversations` and `messages` tables for durable transcript storage, user session tracking, and compliance audits.
  5. **Token-Saving Conversational Fast-Path**:
     * Intercepts routine pleasantries (greetings, thanks, farewells, help) before any vector search or model invocation.
     * Returns instant response with zero token usage, sub-5ms latency, and seamless conversation history recording.

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
| **Guardrails** | Custom Regex & Heuristic Fast-Path | Prompt injection defense, token-saving pleasantries, hallucination checking |
| **Experiment Tracking** | MLflow | Retrieval parameter tuning, prompt evaluations, metric logging |
| **Data Versioning** | DVC | Versioning gold evaluation benchmarks and test datasets |
| **Observability** | Langfuse | Distributed LLM tracing, latency, token, and cost tracking |
| **CI/CD** | GitHub Actions | Automated linting, test suites, and evaluation metric gates |

