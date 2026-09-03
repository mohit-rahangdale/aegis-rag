"""Conversation inspection and history management endpoints."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.conversation import ConversationRepository
from app.db.session import get_db
from app.memory.manager import ConversationMemoryManager

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class MessageDetail(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageDetail] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


@router.get(
    "",
    response_model=List[ConversationSummary],
    summary="List Conversations",
    description="List active conversations with pagination.",
)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationSummary]:
    """Retrieve list of conversation sessions."""
    repo = ConversationRepository(db)
    convs = await repo.list_conversations(limit=limit, offset=offset)
    return [
        ConversationSummary(
            id=c.id,
            title=c.title,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in convs
    ]


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get Conversation History",
    description="Fetch a conversation and all its chronological message turns.",
)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    """Retrieve full conversation transcript."""
    repo = ConversationRepository(db)
    conv = await repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=[
            MessageDetail(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
                meta_info=m.meta_info or {},
            )
            for m in conv.messages
        ],
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Conversation",
    description="Delete a conversation from both Redis cache and database.",
)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete conversation session and message history."""
    memory = ConversationMemoryManager(db)
    deleted = await memory.clear_conversation(conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )
