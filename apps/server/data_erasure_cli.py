"""Private development operator command. One bounded JSON request arrives on stdin.

JWT/operation keys never appear in argv or error output. No production account
closure or public maintenance/recovery endpoint is provided.
"""

import json
import sys
from uuid import UUID

from app.auth.jwt_verifier import JWTBearerVerifier
from app.chat_import.artifacts import LocalFilesystemImportArtifactStore
from app.core.config import get_settings
from app.db.session import Database
from app.schemas.lifecycle import LifecycleExecute, LifecycleTarget
from app.services.agent_recovery import AgentRunRecovery
from app.services.agent_service import actor_from_verified_identity
from app.services.agent_writer import AgentWriterRegistry
from app.services.erasure import ErasureError
from app.services.lifecycle_erasure import LifecycleErasure


def main():
    database = None
    try:
        config = get_settings()
        if config.app_env not in {"development", "test"}:
            raise ValueError()
        request = json.loads(sys.stdin.readline(16385))
        actor = actor_from_verified_identity(
            JWTBearerVerifier(config).verify(request["credential"]).user_id
        )
        database = Database(config)
        writers = AgentWriterRegistry(config.chat_import_artifact_root)
        service = LifecycleErasure(
            database.session,
            LocalFilesystemImportArtifactStore(config.chat_import_artifact_root),
            writers,
        )
        action = request["action"]
        if action == "recover_run":
            result = AgentRunRecovery(database.session, writers).recover(
                actor,
                UUID(request["conversation_id"]),
                UUID(request["run_id"]),
                request["operation_key"],
            )
        elif action == "owned_prepare":
            result = service.prepare(
                actor, LifecycleTarget(domain="owner", target_id=actor.user_id)
            ).model_dump(mode="json")
        elif action == "owned_execute":
            if request.get("explicit_confirmation") != "ERASE OWNED DATA " + str(actor.user_id):
                raise ValueError()
            body = LifecycleExecute(
                domain="owner",
                target_id=actor.user_id,
                confirmation_id=UUID(request["confirmation_id"]),
                operation_key=request["operation_key"],
            )
            result = service.execute(actor, body).model_dump(mode="json")
        elif action == "receipt":
            result = service.receipt(actor, UUID(request["receipt_id"])).model_dump(mode="json")
        else:
            raise ValueError()
        print(json.dumps(result))
        return 0
    except ErasureError as error:
        allowed = {
            "writer_proof_unavailable",
            "effects_unresolved",
            "target_busy",
            "shared_reference",
            "not_found",
            "target_changed",
            "confirmation_expired",
            "idempotency_conflict",
            "invalid_credential",
            "persistence_failure",
        }
        reason = error.code if error.code in allowed else "authoritative_operator_review_required"
        print(json.dumps({"status": "failed", "reason": reason}))
        return 1
    except Exception:
        print('{"status":"failed","reason":"authoritative_operator_review_required"}')
        return 1
    finally:
        if database is not None:
            database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
