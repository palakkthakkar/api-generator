"""
Async client that batches and ships telemetry to the ingestion server.
Key design decisions:
  - Async queue + background flush thread (non-blocking to the user's app)
  - Batching (don't HTTP on every request — that kills latency)
  - Graceful degradation (if server is down, drop telemetry, don't crash the app)
"""

import asyncio
import threading
import time
import logging
from collections import deque
from dataclasses import dataclass, asdict, field
from typing import Optional
import httpx

logger = logging.getLogger("sentinel_sdk")


@dataclass
class TelemetryEvent:
    """Single API request telemetry record."""
    endpoint: str           # e.g., "/api/checkout"
    method: str             # e.g., "POST"
    status_code: int        # e.g., 200
    latency_ms: float       # e.g., 42.3
    request_size: int       # bytes
    response_size: int      # bytes
    timestamp: float        # unix epoch
    app_name: str = ""
    metadata: dict = field(default_factory=dict)


class SentinelClient:
    """
    Buffers telemetry events and flushes to the ingestion server in batches.
    
    Usage:
        client = SentinelClient(server_url="http://localhost:8100", app_name="my-service")
        client.track(event)
        # ... on shutdown:
        client.shutdown()
    """

    def __init__(
        self,
        server_url: str,
        app_name: str = "default",
        flush_interval: float = 5.0,    # seconds between flushes
        batch_size: int = 100,           # max events per flush
        max_queue_size: int = 10_000,    # drop if queue overflows
    ):
        self.server_url = server_url.rstrip("/")
        self.app_name = app_name
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size

        self._queue: deque[TelemetryEvent] = deque(maxlen=max_queue_size)
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        self._client = httpx.Client(timeout=5.0)

        logger.info(f"SentinelSDK initialized → {self.server_url}")

    def track(self, event: TelemetryEvent):
        """Add a telemetry event to the buffer. Non-blocking."""
        event.app_name = self.app_name
        self._queue.append(event)

    def _flush_loop(self):
        """Background thread: periodically flushes buffered events."""
        while self._running:
            time.sleep(self.flush_interval)
            self._flush()

    def _flush(self):
        """Send one batch to the ingestion server."""
        if not self._queue:
            return

        batch = []
        while self._queue and len(batch) < self.batch_size:
            batch.append(asdict(self._queue.popleft()))

        try:
            resp = self._client.post(
                f"{self.server_url}/api/v1/ingest",
                json={"events": batch},
            )
            if resp.status_code != 200:
                logger.warning(f"Ingestion server returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed to flush telemetry: {e}")
            # Don't re-queue — graceful degradation over back-pressure

    def shutdown(self):
        """Flush remaining events and stop the background thread."""
        self._running = False
        self._flush()  # final flush
        self._client.close()