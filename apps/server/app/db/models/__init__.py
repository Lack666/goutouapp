"""Minimal Phase 2B tables. Import this module to register all metadata."""

from app.db.models.admission import AdmissionState, UploadReservation
from app.db.models.erasure import ErasureConfirmation, ErasureReceipt
from app.db.models.import_jobs import (
    ChatImportArtifact,
    ChatImportJob,
    ChatImportSpeaker,
    RelationshipMessage,
)
from app.db.models.lifecycle import LifecycleConfirmation, LifecycleReceipt, RunRecoveryReceipt
from app.db.models.records import (
    AgentRun,
    Conversation,
    MemoryConfirmationRow,
    MemoryControlRow,
    MemoryMutationRow,
    MemoryOperationRow,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    User,
)

__all__ = [
    "LifecycleConfirmation",
    "LifecycleReceipt",
    "RunRecoveryReceipt",
    "ErasureConfirmation",
    "ErasureReceipt",
    "AdmissionState",
    "UploadReservation",
    "ChatImportArtifact",
    "ChatImportJob",
    "ChatImportSpeaker",
    "RelationshipMessage",
    "AgentRun",
    "Conversation",
    "MemoryControlRow",
    "MemoryConfirmationRow",
    "MemoryMutationRow",
    "MemoryOperationRow",
    "MemoryRecordRow",
    "Message",
    "Person",
    "Relationship",
    "User",
]
