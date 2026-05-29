"""
Reads raw telemetry from Redis Streams, computes 1-minute metric windows,
and stores aggregated features in PostgreSQL.

Run as: python -m app.workers.aggregator
"""

import asyncio
import json
import time
import numpy as np
from collections import defaultdict
from datetime import datetime, timezone
import redis.asyncio as aioredis
from ..config import settings
from ..models.database import SessionLocal, MetricWindow
from ..ml.detector import AnomalyDetector

WINDOW_SEC = settings.aggregation_window_sec  # 60 seconds


class FeatureAggregator:
    def __init__(self):
        self.redis = None
        self.buffers = defaultdict(list)   # stream_key → [events in current window]
        self.window_starts = {}            # stream_key → window start time
        self.detectors = {}                # stream_key → AnomalyDetector
        self.consumer_group = "aggregator"
        self.consumer_name = "worker-1"

    async def start(self):
        """Main loop: discover streams, read events, aggregate, store."""
        self.redis = aioredis.from_url(settings.redis_url)
        print("[Aggregator] Started. Watching for telemetry streams...")

        while True:
            # Discover all telemetry streams
            streams = []
            async for key in self.redis.scan_iter("telemetry:*"):
                key_str = key.decode() if isinstance(key, bytes) else key
                streams.append(key_str)
                # Ensure consumer group exists
                try:
                    await self.redis.xgroup_create(key_str, self.consumer_group, id="0", mkstream=True)
                except Exception:
                    pass  # group already exists

            if not streams:
                await asyncio.sleep(2)
                continue

            # Read from each stream
            for stream_key in streams:
                try:
                    messages = await self.redis.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        streams={stream_key: ">"},
                        count=500,
                        block=100,
                    )
                except Exception as e:
                    continue

                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        raw = fields.get(b"data") or fields.get("data")
                        if raw:
                            event = json.loads(raw)
                            sk = stream_key
                            
                            # Initialize window if needed
                            if sk not in self.window_starts:
                                self.window_starts[sk] = time.time()

                            self.buffers[sk].append(event)

                        # Acknowledge
                        await self.redis.xack(stream_key, self.consumer_group, msg_id)

            # Check if any windows are complete
            now = time.time()
            for sk in list(self.buffers.keys()):
                if now - self.window_starts.get(sk, now) >= WINDOW_SEC:
                    if self.buffers[sk]:
                        await self._aggregate_and_store(sk, self.buffers[sk])
                    self.buffers[sk] = []
                    self.window_starts[sk] = now

            await asyncio.sleep(0.5)

    async def _aggregate_and_store(self, stream_key: str, events: list):
        """Compute aggregated features from raw events and store in DB."""
        # Parse stream key: telemetry:{app_name}:{endpoint}
        parts = stream_key.split(":", 2)
        app_name = parts[1] if len(parts) > 1 else "unknown"
        endpoint = parts[2] if len(parts) > 2 else "unknown"

        latencies = [e["latency_ms"] for e in events]
        status_codes = [e["status_code"] for e in events]
        req_sizes = [e["request_size"] for e in events]
        resp_sizes = [e["response_size"] for e in events]

        error_count = sum(1 for s in status_codes if s >= 400)

        window = MetricWindow(
            app_name=app_name,
            endpoint=endpoint,
            window_start=datetime.now(timezone.utc),
            request_count=len(events),
            error_count=error_count,
            error_rate=error_count / len(events) if events else 0,
            latency_p50=float(np.percentile(latencies, 50)),
            latency_p95=float(np.percentile(latencies, 95)),
            latency_p99=float(np.percentile(latencies, 99)),
            latency_mean=float(np.mean(latencies)),
            latency_std=float(np.std(latencies)) if len(latencies) > 1 else 0.0,
            avg_request_size=float(np.mean(req_sizes)),
            avg_response_size=float(np.mean(resp_sizes)),
        )

        # Store in PostgreSQL
        db = SessionLocal()
        try:
            db.add(window)
            db.commit()
            print(f"[Aggregator] Stored window: {endpoint} | "
                  f"{len(events)} reqs | p95={window.latency_p95:.1f}ms | "
                  f"err_rate={window.error_rate:.2%}")
        finally:
            db.close()

        # Also publish to Redis for real-time consumers (dashboard)
        await self.redis.publish(
            f"metrics:{app_name}:{endpoint}",
            json.dumps({
                "endpoint": endpoint,
                "app_name": app_name,
                "request_count": window.request_count,
                "error_rate": window.error_rate,
                "latency_p50": window.latency_p50,
                "latency_p95": window.latency_p95,
                "latency_p99": window.latency_p99,
                "latency_mean": window.latency_mean,
                "timestamp": window.window_start.isoformat(),
            })
        )

        # Evaluate the window for anomalies and publish if detected.
        await self._detect_anomaly(window)

    async def _detect_anomaly(self, window: MetricWindow):
        """Score the aggregated window and publish anomaly events."""
        stream_key = f"telemetry:{window.app_name}:{window.endpoint}"
        detector = self.detectors.get(stream_key)
        if detector is None:
            detector = AnomalyDetector(model_dir="models")
            self.detectors[stream_key] = detector

        if not detector.is_trained:
            trained = detector.train_on_history(
                window.app_name,
                window.endpoint,
                min_windows=settings.min_training_windows,
            )
            if not trained:
                return

        result = detector.evaluate(window)
        if result and result.get("is_anomaly"):
            anomaly_payload = {
                "endpoint": window.endpoint,
                "app_name": window.app_name,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "severity": result["severity"],
                "score": result["autoencoder"]["anomaly_score"],
                "features": result["autoencoder"]["top_contributing_features"],
            }
            print(f"[Aggregator] Anomaly detected on {window.endpoint}: {anomaly_payload['severity']:.2f}")
            await self.redis.publish(
                f"anomaly:{window.app_name}:{window.endpoint}",
                json.dumps(anomaly_payload),
            )


async def main():
    agg = FeatureAggregator()
    await agg.start()


if __name__ == "__main__":
    asyncio.run(main())