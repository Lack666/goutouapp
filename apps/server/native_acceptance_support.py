"""Opt-in disposable Android fixture controls; never installed on the real API."""

import asyncio
import json
from hashlib import sha256
from threading import Event

import jwt
from memory_phase6_support import Phase6Mock


class NativeAcceptanceMock(Phase6Mock):
    def __init__(self):
        super().__init__()
        self.fail_next = False
        self.delay = 0.8
        self.response_release = Event()
        self.response_release.set()

    async def structured_output(self, messages, schema, **kwargs):
        await asyncio.sleep(self.delay)
        if schema.__name__ == "ResponseResult":
            if not await asyncio.to_thread(self.response_release.wait, 90):
                raise RuntimeError("Controlled final response barrier timed out")
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("Controlled synthetic provider failure")
        value = await super().structured_output(messages, schema, **kwargs)
        if schema.__name__ == "ResponseResult":
            value = value.model_copy(update={"final_answer": value.final_answer + " 合成验收🌱"})
        return value


class NativeAcceptanceWire:
    """One-shot faults happen after the unchanged service has produced its reply.

    No bodies, credentials, query values or model payloads are retained. A dropped
    REST response closes an incomplete HTTP body after the database commit. A
    stream disconnect exposes its first status, then EOF; the unchanged transport
    disconnect policy determines the server outcome. These are fixture-only
    transport faults, not API shortcuts.
    """

    def __init__(self, app, owners):
        self.app = app
        self.owners = owners
        self.fault = None
        self.requests = []
        self.fired = []
        self.hold_path = None
        self.release = Event()
        self.release.set()

    def arm(self, fault):
        if fault not in {"agent_drop", "memory_drop", "erasure_drop", "sse_disconnect"}:
            raise ValueError("Unsupported synthetic fault")
        if self.fault:
            raise ValueError("A synthetic fault is already armed")
        self.fault = fault

    def hold(self, path):
        if path not in {"/api/v1/memories", "/messages"}:
            raise ValueError("Unsupported synthetic held GET")
        self.hold_path = path
        self.release.clear()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        method = scope["method"]
        headers = dict(scope["headers"])
        proof = {
            "method": method,
            "path": path,
            "bearer": headers.get(b"authorization", b"").startswith(b"Bearer "),
            "json": headers.get(b"content-type", b"").startswith(b"application/json"),
            "cursor": b"cursor=" in scope.get("query_string", b""),
            "host_setup": headers.get(b"user-agent", b"").startswith(b"python-httpx"),
        }
        settings = self.app.state.settings
        try:
            claims = jwt.decode(
                headers.get(b"authorization", b"").decode().removeprefix("Bearer "),
                settings.auth_jwt_secret.get_secret_value() if settings.auth_jwt_secret else "",
                algorithms=["HS256"],
                issuer=settings.auth_jwt_issuer,
                audience=settings.auth_jwt_audience,
            )
            proof["verified_owner"] = self.owners.get(claims["sub"], "unrecognized")
        except (jwt.PyJWTError, UnicodeError, KeyError):
            proof["verified_owner"] = "invalid"
        self.requests.append(proof)
        if method == "POST" and path == "/api/v1/erasures/execute":
            original_receive = receive
            digest = sha256()

            async def receive():
                message = await original_receive()
                if message["type"] == "http.request":
                    digest.update(message.get("body", b""))
                    if not message.get("more_body", False):
                        proof["body_sha256"] = digest.hexdigest()
                return message

        self.requests[:] = self.requests[-500:]
        fault = self.fault
        matches = method == "POST" and (
            (fault == "agent_drop" and path.endswith("/agent-runs"))
            or (fault == "erasure_drop" and path == "/api/v1/erasures/execute")
            or (
                fault == "memory_drop"
                and "/memory/deletions/" in path
                and path.endswith("/execute")
            )
            or (fault == "sse_disconnect" and path.endswith("/agent-runs/stream"))
        )
        if matches:
            self.fault = None
        else:
            fault = None
        start = None
        disconnected = False
        held = method == "GET" and self.hold_path and path.endswith(self.hold_path)
        if held:
            self.hold_path = None
            self.fired.append({"fault": "held_get", "path": path})

        async def observed_send(message):
            nonlocal start, disconnected
            if message["type"] == "http.response.start":
                proof["status"] = message["status"]
                start = message
                if held:
                    if not await asyncio.to_thread(self.release.wait, 180):
                        raise RuntimeError("Controlled GET barrier timed out")
                if (
                    fault in {"agent_drop", "memory_drop", "erasure_drop"}
                    and message["status"] < 300
                ):
                    return
            if message["type"] == "http.response.body" and start and start["status"] < 300:
                if fault in {"agent_drop", "memory_drop", "erasure_drop"}:
                    if not message.get("more_body", False):
                        self.fired.append({"fault": fault, "path": path, "status": start["status"]})
                        await send(start)
                        await send({"type": "http.response.body", "body": b"", "more_body": True})
                        raise RuntimeError("Controlled response loss after service commit")
                    return
                if fault == "sse_disconnect":
                    if disconnected:
                        return
                    await send(message)
                    if b"event: status\n" in message.get("body", b""):
                        self.fired.append({"fault": fault, "path": path, "status": start["status"]})
                        await send({"type": "http.response.body", "body": b"", "more_body": False})
                        disconnected = True
                    return
            await send(message)

        await self.app(scope, receive, observed_send)

    def evidence(self):
        # Round-trip makes snapshots independent of subsequent server callbacks.
        return json.loads(json.dumps({"requests": self.requests, "faults": self.fired}))
