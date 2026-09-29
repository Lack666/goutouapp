"""Minimal Phase 2B tables. Import this module to register all metadata."""

from app.db.models.import_jobs import (
    ChatImportArtifact,
    ChatImportJob,
    ChatImportSpeaker,
    RelationshipMessage,
)
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
    "ChatImportArtifact",
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
