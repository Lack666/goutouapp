"""Short SQL transactions fence an independent, keyless ICA Runtime execution."""

import hmac
import json
import re
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.db.models import ImportedAnalysisRun
from app.llm.mock import MockLLMProvider
from app.schemas.imported_execution import (
    ExecutionPreparation,
    ExecutionView,
    StoredAnalysisReport,
)
from app.services.imported_analysis import AnalysisError, ImportedAnalysisService, digest

EXECUTION_VERSION = "ica-bq-r1-mock-v2"
EVIDENCE_PROTOCOL = "quote-v2"
MAX_INPUT_BYTES = 128 * 1024
OUTPUT_RESERVE = 8192


def runtime_fingerprint():
    root = Path(__file__).resolve().parents[4]
    return digest(
        [
            (root / path).read_bytes().hex()
            for path in (
                "apps/server/app/agent/imported_analysis.py",
                "apps/server/app/agent/imported_contracts.py",
                "apps/server/app/agent/imported_quote.py",
                "apps/server/app/services/imported_execution.py",
                "knowledge/upstream-manifest.json",
                "evals/reference_map.json",
            )
        ]
    )


class ImportedExecutionService(ImportedAnalysisService):
    def __init__(self, sessions, *, enabled=False, provider_factory=None, **kwargs):
        super().__init__(sessions, **kwargs)
        self.enabled, self.provider_factory = enabled, provider_factory

    def available(self):
        if not self.enabled:
            raise AnalysisError("mock_execution_disabled")

    def run_owned(self, db, actor, run_id):
        row = db.scalar(
            select(ImportedAnalysisRun).where(
                ImportedAnalysisRun.id == run_id,
                ImportedAnalysisRun.owner_user_id == actor.user_id,
            )
        )
        if row is None:
            raise AnalysisError()
        return row

    def current_run(self, db, actor, row):
        if row.expires_at <= self.clock() or row.status in {
            "revoked",
            "expired",
            "deleted",
            "restore_invalid",
        }:
            raise AnalysisError("execution_inactive")
        grant = self.owned(db, actor, row.grant_id)
        contexts = self.current(db, actor, grant)
        if row.execution_binding.get("grant_binding") != grant.binding_hash:
            raise AnalysisError("source_changed")
        if row.execution_binding.get("runtime_digest") != runtime_fingerprint():
            raise AnalysisError("runtime_changed")
        if row.execution_binding.get("evidence_protocol") != EVIDENCE_PROTOCOL:
            raise AnalysisError("runtime_changed")
        return grant, contexts

    @staticmethod
    def run_view(row):
        return ExecutionView(
            run_id=row.id,
            grant_id=row.grant_id,
            status=row.status,
            expires_at=row.expires_at,
            binding_hash=row.binding_hash,
            execution=row.execution_binding,
            mock_calls=row.request_count,
            reserved_tokens=row.reserved_tokens,
            ledger=row.ledger,
            receipts=row.receipts,
            report=StoredAnalysisReport.model_validate_json(json.dumps(row.report))
            if row.report
            else None,
            error_code=row.error_code,
        )

    def prepare_execution(self, actor, body):
        from app.agent.imported_analysis import ImportedAnalysisError, validate_static_inputs

        self.available()
        with self.transaction(actor) as db:
            grant = self.owned(db, actor, body.grant_id)
            contexts = self.current(db, actor, grant)
            if grant.payload["request"]["model"] != "mock":
                raise AnalysisError("mock_model_required")
            if not any(c.messages for c in contexts):
                raise AnalysisError("empty_scope")
            try:
                validate_static_inputs(
                    contexts,
                    grant.payload["request"]["question"],
                    evidence_protocol=EVIDENCE_PROTOCOL,
                )
            except ImportedAnalysisError:
                raise AnalysisError("scope_or_budget_rejected") from None
            execution = {
                "version": EXECUTION_VERSION,
                "evidence_protocol": EVIDENCE_PROTOCOL,
                "runtime_digest": runtime_fingerprint(),
                "grant_binding": grant.binding_hash,
                "model": "mock",
                "provider": "mock",
                "tariff": "keyless-mock-zero-v1",
                "cost_cap": 0,
                "currency": None,
                "request_cap": grant.payload["preview"]["planned_requests"],
                "token_cap": grant.payload["preview"]["token_cap"],
                "max_input_bytes": MAX_INPUT_BYTES,
                "output_token_reserve": OUTPUT_RESERVE,
                "memory_access": False,
                "external_provider_calls": 0,
                "expires_at": grant.expires_at.isoformat(),
            }
            token = secrets.token_urlsafe(32)
            row = ImportedAnalysisRun(
                owner_user_id=actor.user_id,
                grant_id=grant.id,
                dataset_id=grant.dataset_id,
                person_id=grant.person_id,
                relationship_id=grant.relationship_id,
                status="prepared",
                token_hash=digest(token),
                binding_hash=digest(execution),
                challenge_expires_at=min(grant.expires_at, self.clock() + timedelta(minutes=5)),
                expires_at=grant.expires_at,
                execution_binding=execution,
            )
            db.add(row)
            db.flush()
            return ExecutionPreparation(
                preparation_id=row.id,
                challenge=token,
                binding_hash=row.binding_hash,
                expires_at=row.challenge_expires_at,
                execution=execution,
            )

    def confirm_execution(self, actor, body):
        self.available()
        fingerprint = digest(body.model_dump(mode="json"))
        with self.transaction(actor) as db:
            prior = db.scalar(
                select(ImportedAnalysisRun).where(
                    ImportedAnalysisRun.owner_user_id == actor.user_id,
                    ImportedAnalysisRun.operation_key == body.operation_key,
                )
            )
            if prior:
                if prior.confirmation_hash != fingerprint:
                    raise AnalysisError("idempotency_conflict")
                self.current_run(db, actor, prior)
                return self.run_view(prior)
            row = self.run_owned(db, actor, body.preparation_id)
            self.current_run(db, actor, row)
            if row.status != "prepared" or row.challenge_expires_at <= self.clock():
                raise AnalysisError("execution_challenge_inactive")
            if not hmac.compare_digest(
                row.token_hash, digest(body.challenge)
            ) or not hmac.compare_digest(row.binding_hash, body.binding_hash):
                raise AnalysisError("challenge_mismatch")
            row.status, row.token_hash = "authorized", ""
            row.operation_key, row.confirmation_hash = body.operation_key, fingerprint
            return self.run_view(row)

    def inspect_execution(self, actor, run_id):
        with self.transaction(actor) as db:
            row = self.run_owned(db, actor, run_id)
            self.current_run(db, actor, row)
            return self.run_view(row)

    async def execute(self, actor, run_id):
        from app.agent.imported_analysis import (
            ImportedAnalysisError,
            ImportedAnalysisRuntime,
            serialized_request_bytes,
        )

        self.available()
        with self.transaction(actor) as db:
            row = self.run_owned(db, actor, run_id)
            grant, contexts = self.current_run(db, actor, row)
            if row.status in {"completed", "safety_exit", "failed", "running"}:
                return self.run_view(row)
            if row.status != "authorized":
                raise AnalysisError("execution_confirmation_required")
            if self.provider_factory is None:
                raise AnalysisError("mock_fixture_required")
            provider = self.provider_factory()
            # This stage cannot acquire an external Provider even through configuration.
            if not isinstance(provider, MockLLMProvider):
                raise AnalysisError("mock_provider_required")
            question = grant.payload["request"]["question"]
            writer = uuid4().hex
            row.status, row.writer_active, row.writer_token = "running", True, writer

        async def before_call(stage, chunk_id, messages, schema):
            input_bytes = serialized_request_bytes(messages, schema, "mock")
            reserved = input_bytes + 4096 + OUTPUT_RESERVE
            with self.transaction(actor) as db:
                row = self.run_owned(db, actor, run_id)
                self.current_run(db, actor, row)
                if row.status != "running" or row.writer_token != writer:
                    raise AnalysisError("execution_inactive")
                if (
                    input_bytes > MAX_INPUT_BYTES
                    or row.request_count + 1 > row.execution_binding["request_cap"]
                    or row.reserved_tokens + reserved > row.execution_binding["token_cap"]
                ):
                    raise AnalysisError("execution_budget_exceeded")
                call_id = uuid4().hex
                row.ledger = [
                    *row.ledger,
                    {
                        "id": call_id,
                        "stage": stage,
                        "chunk_id": chunk_id,
                        "status": "admitted",
                        "input_bytes": input_bytes,
                        "reserved_tokens": reserved,
                    },
                ]
                row.request_count += 1
                row.reserved_tokens += reserved
                return call_id

        async def after_call(call_id, output, error_code):
            # Never persist intermediate model output or private quotes in the call ledger.
            with self.transaction(actor) as db:
                row = self.run_owned(db, actor, run_id)
                self.current_run(db, actor, row)
                if row.writer_token != writer or row.status != "running":
                    raise AnalysisError("execution_inactive")
                row.ledger = [
                    {**item, "status": "failed" if error_code else "succeeded"}
                    if item["id"] == call_id
                    else item
                    for item in row.ledger
                ]
                if error_code is None:
                    item = next(item for item in row.ledger if item["id"] == call_id)
                    row.receipts = [
                        *row.receipts,
                        {
                            "chunk_id": item["chunk_id"],
                            "stage": item["stage"],
                            "status": "completed",
                        },
                    ]

        try:
            result = await ImportedAnalysisRuntime(
                provider, evidence_protocol=EVIDENCE_PROTOCOL
            ).run(contexts, question, "mock", before_call, after_call)
            report = result.report.model_dump(mode="json")
            if len(json.dumps(report, ensure_ascii=False).encode()) > 32 * 1024:
                raise AnalysisError("report_budget_exceeded")
            with self.transaction(actor) as db:
                row = self.run_owned(db, actor, run_id)
                grant, _ = self.current_run(db, actor, row)
                if row.status != "running" or row.writer_token != writer:
                    raise AnalysisError("execution_inactive")
                used_ids = set(
                    re.findall(
                        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                        json.dumps(report),
                    )
                )
                row.report = {
                    **report,
                    "source": {
                        "grant_id": str(grant.id),
                        "owner_id": str(actor.user_id),
                        "dataset_id": str(grant.dataset_id),
                        "person_id": str(grant.person_id),
                        "relationship_id": str(grant.relationship_id),
                        "binding_hash": grant.binding_hash,
                        "preview": grant.payload["preview"],
                        "aliases": {
                            alias: {"message_id": ref["id"], "window": ref["window"]}
                            for alias, ref in grant.payload["aliases"].items()
                            if ref["id"] in used_ids
                        },
                    },
                }
                # Receipts are metadata only; source text lives solely in the temporary report.
                row.receipts = [receipt.model_dump(mode="json") for receipt in result.receipts]
                if (
                    len(
                        json.dumps(
                            {
                                "report": row.report,
                                "ledger": row.ledger,
                                "receipts": row.receipts,
                                "execution_binding": row.execution_binding,
                            },
                            ensure_ascii=False,
                        ).encode()
                    )
                    > 128 * 1024
                ):
                    raise AnalysisError("report_budget_exceeded")
                row.status = "safety_exit" if report["outcome"] == "safety_blocked" else "completed"
        except BaseException as exc:
            with self.transaction(actor) as db:
                row = db.get(ImportedAnalysisRun, run_id)
                if row and row.writer_token == writer and row.status == "running":
                    row.status, row.report = "failed", None
                    row.error_code = (
                        exc.code
                        if isinstance(exc, (AnalysisError, ImportedAnalysisError))
                        else "runtime_failed"
                    )
            if not isinstance(exc, Exception):
                raise
        finally:
            with self.transaction(actor) as db:
                row = db.get(ImportedAnalysisRun, run_id)
                if row:
                    row.writer_active, row.writer_token = False, None
        return self.inspect_execution(actor, run_id)
