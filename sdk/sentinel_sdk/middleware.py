"""
Drop-in middleware for FastAPI.
Usage:
    from sentinel_sdk import SentinelMiddleware
    app.add_middleware(SentinelMiddleware, server_url="http://localhost:8100")
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from .client import SentinelClient, TelemetryEvent


class SentinelMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, server_url: str, app_name: str = "default", **kwargs):
        super().__init__(app)
        self.client = SentinelClient(server_url=server_url, app_name=app_name, **kwargs)

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        # Read request body size (without consuming the stream for the app)
        body = await request.body()
        request_size = len(body)

        response = await call_next(request)

        latency_ms = (time.perf_counter() - start) * 1000

        # Capture response size from content-length header if available
        response_size = int(response.headers.get("content-length", 0))

        event = TelemetryEvent(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            request_size=request_size,
            response_size=response_size,
            timestamp=time.time(),
        )

        self.client.track(event)
        return response