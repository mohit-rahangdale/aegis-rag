"""Repository layer for Conversation and Message database operations."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.conversation import Conversation, Message


class ConversationRepository:
    """Async repository for conversations and message history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_conversation(
        self,
        conversation_id: Optional[str] = None,
        title: str = "New Conversation",
        meta_info: Optional[Dict[str, Any]] = None,
    ) -> Conversation:
        """Create a new conversation session."""
        conv = Conversation(
            title=title,
            meta_info=meta_info or {},
        )
        if conversation_id:
            conv.id = str(conversation_id)

        self.session.add(conv)
        await self.session.flush()
        return conv

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Fetch conversation by ID including its messages."""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == str(conversation_id))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        conversation_id: Optional[str] = None,
        title: str = "New Conversation",
    ) -> Conversation:
        """Fetch existing conversation or create a new one."""
        if conversation_id:
            existing = await self.get_conversation(conversation_id)
            if existing:
                return existing
        return await self.create_conversation(conversation_id=conversation_id, title=title)

    async def list_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Conversation]:
        """List conversations ordered by updated_at descending."""
        query = (
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its cascaded messages."""
        await self.session.execute(
            delete(Message).where(Message.conversation_id == str(conversation_id))
        )
        query = delete(Conversation).where(Conversation.id == str(conversation_id))
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount > 0


    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        meta_info: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Append a message to a conversation."""
        msg = Message(
            conversation_id=str(conversation_id),
            role=role,
            content=content,
            meta_info=meta_info or {},
        )
        self.session.add(msg)

        # Touch conversation updated_at
        conv_query = select(Conversation).where(Conversation.id == str(conversation_id))
        res = await self.session.execute(conv_query)
        conv = res.scalar_one_or_none()
        if conv:
            conv.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        return msg

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Message]:
        """Get chronological messages for a conversation."""
        query = (
            select(Message)
            .where(Message.conversation_id == str(conversation_id))
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
