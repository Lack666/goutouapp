"""Owner erasure uses a signed private pipe and explicit, bounded confirmation."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from test_agent_rest import headers
from test_erasure import erasure_api as legacy_erasure_api  # noqa: F401
from test_full_erasure_9h import full_erasure_api  # noqa: F401


def operator(config, request, *, environment="test"):
    env = os.environ.copy()
    env.update(
        APP_ENV=environment,
        DATABASE_URL=config.database_url.get_secret_value(),
        AUTH_JWT_SECRET=config.auth_jwt_secret.get_secret_value(),
        AUTH_JWT_ISSUER=config.auth_jwt_issuer,
        AUTH_JWT_AUDIENCE=config.auth_jwt_audience,
        CHAT_IMPORT_ARTIFACT_ROOT=str(config.chat_import_artifact_root),
        PYTHONUTF8="1",
    )
    result = subprocess.run(
        [sys.executable, "apps/server/data_erasure_cli.py"],
        cwd=Path(__file__).resolve().parents[3],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert request["credential"] not in result.stdout + result.stderr
    assert "Authorization" not in result.stdout + result.stderr
    return result.returncode, json.loads(result.stdout)


def test_signed_owner_cli_strong_confirmation_scope_receipt_replay_and_identity(full_erasure_api):  # noqa: F811
    _, client, a, b, _, _, config = full_erasure_api
    base = {"credential": headers(a[0])["Authorization"].removeprefix("Bearer ")}
    code, challenge = operator(config, {**base, "action": "owned_prepare"})
    assert code == 0 and challenge["domain"] == "owner" and challenge["target_id"] == str(a[0])
    execute = {
        **base,
        "action": "owned_execute",
        "confirmation_id": challenge["confirmation_id"],
        "operation_key": uuid4().hex,
    }
    assert operator(config, execute)[0] == 1
    execute["explicit_confirmation"] = "ERASE OWNED DATA " + str(b[0])
    assert operator(config, execute)[0] == 1
    assert client.get("/api/v1/persons", headers=headers(a[0])).status_code == 200
    execute["explicit_confirmation"] = "ERASE OWNED DATA " + str(a[0])
    code, receipt = operator(config, execute)
    assert code == 0 and receipt["status"] == "deleted"
    assert operator(config, execute) == (0, receipt)
    assert operator(config, {**base, "action": "receipt", "receipt_id": receipt["receipt_id"]}) == (
        0,
        receipt,
    )
    assert client.get("/api/v1/persons", headers=headers(a[0])).status_code == 401
    assert client.get("/api/v1/persons", headers=headers(b[0])).status_code == 200
    other = {
        "credential": headers(b[0])["Authorization"].removeprefix("Bearer "),
        "action": "receipt",
        "receipt_id": receipt["receipt_id"],
    }
    assert operator(config, other)[0] == 1
    expired = {
        **base,
        "credential": headers(a[0], exp=0)["Authorization"].removeprefix("Bearer "),
        "action": "owned_prepare",
    }
    assert operator(config, expired)[0] == 1
    assert operator(config, {**base, "action": "owned_prepare"}, environment="production")[0] == 1


def test_unattributed_raw_file_blocks_owned_data_without_deleting_other_files(full_erasure_api):  # noqa: F811
    _, client, a, b, _, _, config = full_erasure_api
    unknown = config.chat_import_artifact_root / (uuid4().hex + ".part")
    unknown.write_bytes(b"anonymous synthetic unattributed bytes")
    request = {
        "credential": headers(a[0])["Authorization"].removeprefix("Bearer "),
        "action": "owned_prepare",
    }
    try:
        code, result = operator(config, request)
        assert code == 1 and result["reason"] == "shared_reference"
        assert unknown.is_file()
        assert client.get("/api/v1/persons", headers=headers(a[0])).status_code == 200
        assert client.get("/api/v1/persons", headers=headers(b[0])).status_code == 200
    finally:
        unknown.unlink(missing_ok=True)
