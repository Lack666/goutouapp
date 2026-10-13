"""Early signed admission before any multipart receive or business mutation."""

import asyncio
from time import monotonic

from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from app.api.errors import error_response
from app.auth.jwt_verifier import (
    CredentialConfigurationError,
    CredentialVerificationError,
    JWTBearerVerifier,
)
from app.services.resource_admission import AdmissionRejected


class ResourceAdmissionMiddleware:
    def __init__(self, app, admission, settings):
        self.app = app
        self.admission = admission
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        upload = scope["method"] == "POST" and scope["path"] == "/api/v1/chat-imports"
        processing = (
            scope["method"] == "POST"
            and scope["path"].startswith("/api/v1/chat-imports/")
            and scope["path"].endswith("/finalize")
        )
        # Liveness/status/schema contracts remain independent of the DB. Other
        # protected API attempts share the deployment request window. No IP or
        # X-Forwarded-For value is trusted as identity.
        protected = scope["path"].startswith("/api/v1/") and scope["path"] != "/api/v1/status"
        if not protected or scope["method"] == "OPTIONS":
            return await self.app(scope, receive, send)
        owner = None
        credential_error = None
        try:
            values = [v for k, v in scope.get("headers", ()) if k.lower() == b"authorization"]
            if len(values) != 1:
                raise CredentialVerificationError
            scheme, _, token = values[0].decode("latin1").partition(" ")
            if scheme.lower() != "bearer":
                raise CredentialVerificationError
            owner = JWTBearerVerifier(self.settings).verify(token).user_id
        except (CredentialConfigurationError, CredentialVerificationError) as exc:
            credential_error = exc
        lease = None
        started = monotonic()
        try:
            # Keep foundational auth-only failure tests and health startup lazy;
            # configured data deployments fail closed on admission DB failure.
            if self.settings.database_url is not None:
                await run_in_threadpool(self.admission.rate, owner, upload=upload)
            if upload or processing:
                if credential_error is not None:
                    if isinstance(credential_error, CredentialConfigurationError):
                        raise AdmissionRejected(503, "authentication_unavailable")
                    raise AdmissionRejected(401, "invalid_credential")
                task = asyncio.create_task(
                    run_in_threadpool(
                        self.admission.acquire, owner, "upload" if upload else "processing"
                    )
                )
                try:
                    lease = await asyncio.shield(task)
                except BaseException:
                    # Cancellation while a thread is obtaining a slot must not
                    # lose ownership of a successfully acquired connection.
                    try:
                        acquired = await asyncio.shield(task)
                        await run_in_threadpool(self.admission.release, acquired)
                    except AdmissionRejected:
                        pass
                    raise
                scope["admission_artifact_key"] = lease.artifact_key

            async def timed_receive():
                remaining = self.settings.admission_body_total_seconds - (monotonic() - started)
                if remaining <= 0:
                    self.admission.record("body_timeout")
                    raise HTTPException(408)
                try:
                    return await asyncio.wait_for(
                        receive(), min(remaining, self.settings.admission_body_idle_seconds)
                    )
                except TimeoutError:
                    self.admission.record("body_timeout")
                    raise HTTPException(408) from None

            await self.app(scope, timed_receive if upload else receive, send)
        except AdmissionRejected as exc:
            if exc.status in {429, 503}:
                self.admission.record("rate_rejected" if exc.status == 429 else "capacity_rejected")
            await error_response(
                exc.status,
                exc.code,
                "Request temporarily unavailable"
                if exc.status != 401
                else "Valid Bearer credential required",
                {"Retry-After": str(exc.retry_after)}
                if exc.status in {429, 503}
                else {"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
        finally:
            if lease:
                await asyncio.shield(run_in_threadpool(self.admission.release, lease))
