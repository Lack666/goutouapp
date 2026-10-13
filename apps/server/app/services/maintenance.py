"""Operator-only periodic maintenance; fixed count output and OS-owned exclusion."""

import os
from collections.abc import Callable
from datetime import datetime
from threading import Event

from pydantic import BaseModel, Field

from app.retention import RetentionPolicy, utc_now
from app.services.admission_fence import _lock
from app.services.import_workflow import ImportWorkflowService
from app.services.memory_retention import CleanupResult, MemoryRetentionService
from app.services.resource_admission import ResourceAdmission


class MaintenanceResult(BaseModel):
    status: str = "ok"
    memory: CleanupResult | None = None
    artifact_removed: int = 0
    orphan_removed: int = 0
    cleanup_failures: int = 0
    scanned: int = 0
    scan_continues: bool = False
    expired_backlog: int = 0
    occupancy: dict[str, int | dict[str, int]] = Field(default_factory=dict)
    error: str | None = None


class MaintenanceBusy(Exception):
    pass


class MaintenanceService:
    def __init__(
        self,
        admission: ResourceAdmission,
        workflow: ImportWorkflowService,
        *,
        clock: Callable[[], datetime] = utc_now,
        max_batches: int = 10,
    ):
        if not 1 <= max_batches <= 10000:
            raise ValueError("Invalid maintenance bounds")
        self.admission = admission
        self.workflow = workflow
        self.clock = clock
        self.max_batches = max_batches
        self._cursor = None

    def _fence(self):
        # A permanent lock inode avoids unlink/recreate races between operators.
        path = self.admission.root.parent / (".maintenance-" + self.admission.scope_key[:16])
        if path.is_symlink():
            raise OSError("Invalid maintenance fence")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        file = os.fdopen(os.open(path, flags, 0o600), "r+b")
        try:
            if file.seek(0, 2) == 0:
                file.write(b"0")
                file.flush()
            try:
                _lock(file)
            except OSError as exc:
                if exc.errno in {11, 13}:
                    raise MaintenanceBusy from None
                raise
            return file
        except BaseException:
            file.close()
            raise

    def run(self) -> MaintenanceResult:
        result = MaintenanceResult()
        fence = None
        try:
            try:
                fence = self._fence()
            except MaintenanceBusy:
                result.status = "skipped"
                result.error = "maintenance_busy"
                return result
            self.admission.snapshot()  # Recover only OS-proven dead workers.
            retention = MemoryRetentionService(
                self.admission.database.session,
                policy=RetentionPolicy.from_settings(self.admission.settings),
                clock=self.clock,
            )
            result.memory = retention.run(dry_run=False, max_batches=self.max_batches)
            cleanup = self.workflow.cleanup_pass(
                now=self.clock(), max_batches=self.max_batches, start_after=self._cursor
            )
            self._cursor = cleanup.next_cursor
            result.artifact_removed = cleanup.removed
            result.orphan_removed = cleanup.orphans
            result.cleanup_failures = cleanup.failures
            result.scanned = cleanup.scanned
            result.scan_continues = cleanup.next_cursor is not None
            backlog = retention.run(dry_run=True)
            result.expired_backlog = backlog.counts.memory_records
            result.occupancy = self.admission.snapshot()
            if result.memory.status != "ok" or backlog.status != "ok" or cleanup.failures:
                result.status = "failed"
                result.error = "maintenance_retry_required"
        except Exception:
            result.status = "failed"
            result.error = "maintenance_unavailable"
        finally:
            if fence is not None:
                fence.close()
        return result


class MaintenanceLoop:
    def __init__(self, service: MaintenanceService, *, interval_seconds: float = 60):
        if not 0.01 <= interval_seconds <= 86400:
            raise ValueError("Invalid maintenance interval")
        self.service = service
        self.interval = interval_seconds
        self.failures = 0
        self.executions = 0

    def run(
        self,
        stop: Event,
        *,
        iterations: int | None = None,
        report: Callable[[MaintenanceResult], None] = lambda result: None,
    ) -> None:
        if iterations is not None and iterations < 1:
            raise ValueError("Invalid iteration count")
        while not stop.is_set():
            result = self.service.run()
            self.executions += 1
            self.failures += result.status == "failed"
            report(result)
            if iterations is not None and self.executions >= iterations:
                break
            # Periodic execution with interruptible wait; failed passes retry here.
            if stop.wait(self.interval):
                break
