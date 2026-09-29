"""Bound multipart request bytes before Starlette finishes form spooling."""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.errors import error_response

FORM_OVERHEAD_BYTES = 1024 * 1024


class ImportUploadBodyLimit:
    def __init__(self, app: ASGIApp, max_file_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_file_bytes + FORM_OVERHEAD_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] != "/api/v1/chat-imports"
        ):
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", ()))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = 0
        if length > self.max_body_bytes:
            await error_response(413, "upload_too_large", "Upload exceeds configured limit")(
                scope, receive, send
            )
            return
        consumed = 0

        async def bounded_receive():
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_body_bytes:
                    # FastAPI rethrows HTTPException from body parsing but
                    # converts arbitrary receive exceptions into HTTP 400.
                    raise HTTPException(status_code=413)
            return message

        await self.app(scope, bounded_receive, send)
