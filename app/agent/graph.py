"""Corrective RAG (CRAG) state machine using LangGraph."""

import uuid
from typing import Any, Dict, List, Optional
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.nodes import (
    generate_node,
    grade_documents_node,
    guardrail_node,
    retrieve_node,
    rewrite_query_node,
    verify_grounding_node,
)
from app.agent.state import CRAGState
from app.memory.manager import ConversationMemoryManager


def _route_after_guardrail(state: CRAGState) -> str:
    """Route to END if safety refusal or fast-path dialogue was triggered, else proceed to retrieve."""
    if state.get("safety_refusal") or state.get("fast_path_response"):
        return END
    return "retrieve"



def _route_after_grade(state: CRAGState) -> str:
    """Route to rewrite if documents are insufficient and retry budget remains."""
    relevant = state.get("relevant_documents", [])
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 1)

    if relevant or iteration >= max_iter:
        return "generate"
    return "rewrite"


def build_crag_graph():
    """Construct and compile the Corrective RAG state graph."""
    workflow = StateGraph(CRAGState)

    # 1. Register state nodes
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade", grade_documents_node)
    workflow.add_node("rewrite", rewrite_query_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("verify", verify_grounding_node)

    # 2. Configure edges and entry point
    workflow.set_entry_point("guardrail")

    workflow.add_conditional_edges(
        "guardrail",
        _route_after_guardrail,
        {END: END, "retrieve": "retrieve"},
    )
    workflow.add_edge("retrieve", "grade")

    workflow.add_conditional_edges(
        "grade",
        _route_after_grade,
        {"generate": "generate", "rewrite": "rewrite"},
    )
    workflow.add_edge("rewrite", "retrieve")
    workflow.add_edge("generate", "verify")
    workflow.add_edge("verify", END)

    return workflow.compile()


# Singleton compiled graph instance
crag_app = build_crag_graph()


async def run_crag_pipeline(
    query: str,
    conversation_id: Optional[str] = None,
    db_session: Optional[AsyncSession] = None,
    max_iterations: int = 1,
) -> Dict[str, Any]:
    """Execute the full Corrective RAG pipeline including memory management."""
    conv_id = conversation_id or str(uuid.uuid4())
    memory = ConversationMemoryManager(db_session) if db_session else None

    # 1. Fetch recent conversation history
    history: List[Dict[str, str]] = []
    if memory:
        history = await memory.get_recent_history(conv_id, limit=6)

    # 2. Initial state
    initial_state: CRAGState = {
        "query": query,
        "rewritten_query": None,
        "conversation_id": conv_id,
        "history": history,
        "documents": [],
        "relevant_documents": [],
        "generation": "",
        "citations": [],
        "is_grounded": False,
        "safety_refusal": None,
        "fast_path_response": None,
        "iteration": 0,

        "max_iterations": max_iterations,
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "error": None,
    }

    # 3. Execute LangGraph workflow
    final_state = await crag_app.ainvoke(initial_state)

    # 4. Save turn to memory if not a safety refusal and db_session present
    if memory and not final_state.get("safety_refusal"):
        await memory.record_turn(
            conversation_id=conv_id,
            user_content=query,
            assistant_content=final_state.get("generation", ""),
            turn_metadata={
                "citations": final_state.get("citations", []),
                "token_usage": final_state.get("token_usage", {}),
                "is_grounded": final_state.get("is_grounded", False),
            },
        )

    return final_state
