"""Conversation use cases; no transport or Agent runtime logic."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Conversation, Message
from app.db.repositories import records


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user_id: UUID, relationship_id: UUID | None = None) -> Conversation:
        return records.create_conversation(self.db, user_id, relationship_id)

    def get(self, user_id: UUID, conversation_id: UUID) -> Conversation | None:
        return records.get_conversation(self.db, user_id, conversation_id)

    def list_for_owner(self, user_id: UUID) -> list[Conversation]:
        return records.list_conversations(self.db, user_id)

    def delete(self, user_id: UUID, conversation_id: UUID) -> bool:
        return records.delete_conversation(self.db, user_id, conversation_id)

    def add_message(
        self,
        user_id: UUID,
        conversation_id: UUID,
        role: str,
        content: str,
        speaker: str | None = None,
    ) -> Message | None:
        return records.create_message(self.db, user_id, conversation_id, role, content, speaker)

    def list_messages(self, user_id: UUID, conversation_id: UUID) -> list[Message]:
        return records.list_messages(self.db, user_id, conversation_id)
