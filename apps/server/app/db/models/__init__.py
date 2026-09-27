"""Minimal Phase 2B tables. Import this module to register all metadata."""

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
