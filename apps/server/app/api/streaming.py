"""SSE transport that closes application streams on every ASGI exit path."""

from collections.abc import AsyncIterator

from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from app.schemas.stream_event import encode_sse, to_network_event
from app.services.agent_stream import AgentServiceStream


async def _frames(stream: AgentServiceStream) -> AsyncIterator[bytes]:
    async for event in stream.events:
        yield encode_sse(to_network_event(event))


class ManagedRunStreamingResponse(StreamingResponse):
    def __init__(self, stream: AgentServiceStream) -> None:
        self._run_stream = stream
        super().__init__(
            _frames(stream),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                await self._run_stream.events.aclose()
            finally:
                # Also covers a disconnect between preflight commit and first byte.
                self._run_stream.cancel_if_running()
