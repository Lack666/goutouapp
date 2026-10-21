"""Per-run OS fence for the tested shared private filesystem deployment."""

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from app.db.models import RunRecoveryReceipt
from app.services.admission_fence import WorkerFence, _lock

# Cancellation may leave executor threads alive. Keep strong process-lifetime
# ownership, even if the HTTP/service object is destroyed.
ACTIVE_WRITERS = {}


class WriterProofUnavailable(Exception):
    pass


class AgentWriterRegistry:
    def __init__(self, artifact_root: Path):
        root = artifact_root.resolve()
        self.scope = sha256(str(root).encode()).hexdigest()
        self.root = root.parent / (".agent-writers-" + self.scope[:16])

    def start(self, token):
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise WriterProofUnavailable()
        return WorkerFence(self.root / (token.hex + ".lock"))

    @contextmanager
    def stopped(self, run):
        # An absent/moved root, legacy row or missing fence is not death evidence.
        if run.writer_token is None or run.writer_scope != self.scope or self.root.is_symlink():
            raise WriterProofUnavailable()
        if run.writer_released:
            # Only the original writer commits this after its runtime has ended.
            yield
            return
        path = self.root / (run.writer_token.hex + ".lock")
        if path.is_symlink() or not path.is_file():
            raise WriterProofUnavailable()
        try:
            with path.open("r+b") as file:
                _lock(file)
                yield
        except OSError:
            raise WriterProofUnavailable() from None

    def require_stopped(self, run):
        if run.writer_token is None or run.writer_released:
            return
        with self.stopped(run):
            pass

    def require_settled(self, db, run):
        if run.recovered_at is None:
            self.require_stopped(run)
            return
        receipt = db.scalar(
            select(RunRecoveryReceipt).where(
                RunRecoveryReceipt.run_id == run.id,
                RunRecoveryReceipt.owner_user_id == run.user_id,
                RunRecoveryReceipt.conversation_id == run.conversation_id,
                RunRecoveryReceipt.writer_token == run.writer_token,
                RunRecoveryReceipt.writer_scope == run.writer_scope,
                RunRecoveryReceipt.performed_at == run.recovered_at,
            )
        )
        if receipt is None or run.status != "failed" or run.failure_code != "writer_stopped":
            raise WriterProofUnavailable()
