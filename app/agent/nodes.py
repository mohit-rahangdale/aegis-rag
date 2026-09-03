"""State graph nodes for Corrective RAG (CRAG) execution."""

from typing import Any, Dict, List

from app.agent.state import CRAGState
from app.gateway.models import ChatMessage, GatewayRequest
from app.gateway.service import LLMGateway

from app.guardrails.service import GuardrailsService
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import Reranker


async def guardrail_node(state: CRAGState) -> Dict[str, Any]:
    """Inspect user input against prompt injection and policy violations."""
    guardrails = GuardrailsService()
    result = guardrails.validate_input(state["query"])

    if not result.is_safe:
        refusal = result.refusal_response or "I cannot process this request due to safety policies."
        return {
            "safety_refusal": refusal,
            "generation": refusal,
            "is_grounded": True,
        }

    # Fast-path for repetitive conversational turns to save tokens
    if result.fast_path_response:
        return {
            "fast_path_response": result.fast_path_response,
            "generation": result.fast_path_response,
            "is_grounded": True,
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    return {"safety_refusal": None, "fast_path_response": None}



async def retrieve_node(
    state: CRAGState,
    retriever: HybridRetriever | None = None,
    reranker: Reranker | None = None,
) -> Dict[str, Any]:
    """Execute hybrid retrieval using active search query (original or rewritten)."""
    search_query = state.get("rewritten_query") or state["query"]
    hybrid = retriever or HybridRetriever()
    ranker = reranker or Reranker()

    # 1. Hybrid retrieval (dense + sparse BM25 with RRF)
    raw_chunks = await hybrid.retrieve(query=search_query, top_k=5)

    # 2. Contextual reranking
    reranked = ranker.rerank(query=search_query, candidates=raw_chunks, top_k=5)

    return {"documents": reranked}


async def grade_documents_node(state: CRAGState) -> Dict[str, Any]:
    """Filter retrieved chunks based on relevance confidence score."""
    docs = state.get("documents", [])
    # Filter documents with score above confidence floor
    relevant = [doc for doc in docs if doc.score >= 0.20]

    return {"relevant_documents": relevant}


async def rewrite_query_node(
    state: CRAGState,
    gateway: LLMGateway | None = None,
) -> Dict[str, Any]:
    """Reformulate query using LLM to improve retrieval precision."""
    current_iteration = state.get("iteration", 0) + 1
    llm = gateway or LLMGateway()

    prompt = (
        f"You are a query optimizer for search engines. "
        f"Rewrite the following user query to be more specific, detailed, and suitable for vector search: "
        f"'{state['query']}'. Output only the rewritten query, nothing else."
    )

    try:
        req = GatewayRequest(prompt=prompt, max_tokens=100, temperature=0.2)
        resp = await llm.generate(req)
        rewritten = resp.content.strip().strip('"').strip("'")
    except Exception:
        rewritten = f"{state['query']} overview details"

    return {
        "rewritten_query": rewritten,
        "iteration": current_iteration,
    }


async def generate_node(
    state: CRAGState,
    gateway: LLMGateway | None = None,
) -> Dict[str, Any]:
    """Generate final grounded answer using LLM gateway with context passages."""
    docs_to_use = state.get("relevant_documents") or state.get("documents", [])
    llm = gateway or LLMGateway()

    # Build context string
    context_blocks: List[str] = []
    citations: List[Dict[str, Any]] = []

    for idx, doc in enumerate(docs_to_use, start=1):
        context_blocks.append(f"[{idx}] {doc.text}")
        citations.append(
            {
                "index": idx,
                "chunk_id": doc.chunk_id,
                "document_id": doc.document_id,
                "filename": doc.filename,
                "page": doc.page_number,
                "score": doc.score,
            }
        )

    context_text = "\n\n".join(context_blocks) if context_blocks else "No relevant context found."

    # Build system instructions and conversation history
    messages: List[ChatMessage] = [
        ChatMessage(
            role="system",
            content=(
                "You are AegisRAG, an accurate, truthful AI assistant. "
                "Answer the user's question using ONLY the provided context blocks. "
                "If the context does not contain enough information to answer, state clearly that "
                "the information is not available in the indexed documents. "
                "Cite sources using [1], [2] corresponding to context blocks."
            ),
        )
    ]

    # Include recent conversation turns if present
    for turn in state.get("history", [])[-4:]:
        messages.append(ChatMessage(role=turn.get("role", "user"), content=turn.get("content", "")))

    user_prompt = (

        f"Context passages:\n{context_text}\n\n"
        f"User Question: {state['query']}\n\n"
        f"Provide a clear, grounded answer:"
    )
    messages.append(ChatMessage(role="user", content=user_prompt))


    try:
        req = GatewayRequest(messages=messages, temperature=0.2, max_tokens=1000)
        resp = await llm.generate(req)
        generation_text = resp.content.strip()
        tokens = {
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "total_tokens": resp.usage.total_tokens,
        }
    except Exception as e:
        generation_text = f"Unable to generate response: {str(e)}"
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    return {
        "generation": generation_text,
        "citations": citations,
        "token_usage": tokens,
    }


async def verify_grounding_node(state: CRAGState) -> Dict[str, Any]:
    """Inspect output with guardrails and verify grounding against retrieved context."""
    guardrails = GuardrailsService()

    # 1. Output guardrail: redact secrets/PII, block prompt leaks
    sanitized_text, output_result = guardrails.validate_output(state.get("generation", ""))

    # 2. Grounding check against retrieved context passages
    docs = state.get("relevant_documents") or state.get("documents", [])
    contexts = [d.text for d in docs]
    grounding_result = guardrails.validate_grounding(
        generation=sanitized_text,
        contexts=contexts,
    )

    return {
        "generation": sanitized_text,
        "is_grounded": grounding_result.is_grounded,
    }

