"""Mock-only execution consent is separate from ICA-A source access."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.agent.imported_contracts import AnalysisReport
from app.schemas.imported_analysis import AnalysisConfirm, Strict


class ExecutionPrepare(Strict):
    grant_id: UUID


class ExecutionConfirm(AnalysisConfirm):
    """preparation_id identifies an execution preparation, never a source grant."""


class ExecutionPreparation(Strict):
    preparation_id: UUID
    challenge: str
    binding_hash: str
    expires_at: datetime
    execution: dict
    external_provider_calls: Literal[0] = 0


class EvidenceAlias(Strict):
    message_id: UUID
    window: int = Field(ge=0, le=1)


class ReportAuthority(Strict):
    grant_id: UUID
    owner_id: UUID
    dataset_id: UUID
    person_id: UUID
    relationship_id: UUID
    binding_hash: str
    aliases: dict[str, EvidenceAlias]
    preview: dict


class StoredAnalysisReport(AnalysisReport):
    source: ReportAuthority


class ExecutionView(Strict):
    run_id: UUID
    grant_id: UUID
    status: str
    expires_at: datetime
    binding_hash: str
    execution: dict
    mock_calls: int = Field(ge=0)
    reserved_tokens: int = Field(ge=0)
    ledger: list[dict]
    receipts: list[dict]
    report: StoredAnalysisReport | None
    error_code: str | None
    external_provider_calls: Literal[0] = 0
