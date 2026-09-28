"""Minimal Phase 2B tables. Import this module to register all metadata."""

from app.db.models.import_jobs import ChatImportJob, ChatImportSpeaker, RelationshipMessage
from app.db.models.records import (
    AgentRun,
    Conversation,
    MemoryControlRow,
    MemoryOperationRow,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    User,
)

__all__ = [
    "ChatImportJob",
    "ChatImportSpeaker",
    "RelationshipMessage",
    "AgentRun",
    "Conversation",
    "MemoryControlRow",
    "MemoryOperationRow",
    "MemoryRecordRow",
    "Message",
    "Person",
    "Relationship",
    "User",
]
