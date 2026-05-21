"""
Orchestrates both ML models and produces a unified anomaly verdict.
Called by the aggregator after each new metric window is computed.
"""

import numpy as np
from ..models.database import SessionLocal, MetricWindow, Anomaly
from .autoencoder import AutoencoderTrainer
from .isolation_forest import IsolationForestDetector
from datetime import datetime, timezone


FEATURE_COLUMNS = [
    "request_count", "error_count", "error_rate",
    "latency_p50", "latency_p95", "latency_p99",
    "latency_mean", "latency_std",
    "avg_request_size", "avg_response_size",
]


class AnomalyDetector:
    def __init__(self, model_dir: str = "models"):
        self.autoencoder = AutoencoderTrainer(model_dir)
        self.iforest = IsolationForestDetector(model_dir)
        self.is_trained = False

    def train_on_history(self, app_name: str, endpoint: str, min_windows: int = 100):
        """Pull historical metric windows from DB and train both models."""
        db = SessionLocal()
        try:
            windows = (
                db.query(MetricWindow)
                .filter_by(app_name=app_name, endpoint=endpoint)
                .order_by(MetricWindow.window_start)
                .all()
            )

            if len(windows) < min_windows:
                print(f"  Not enough data for {endpoint} ({len(windows)}/{min_windows})")
                return False

            # Build feature matrix
            data = np.array([
                [getattr(w, col) for col in FEATURE_COLUMNS]
                for w in windows
            ], dtype=np.float32)

            print(f"  Training on {len(data)} windows for {endpoint}...")
            self.autoencoder.train(data, epochs=100)
            self.iforest.train(data)
            self.is_trained = True
            return True
        finally:
            db.close()

    def evaluate(self, window: MetricWindow) -> dict | None:
        """
        Score a new metric window. Returns anomaly verdict or None if not trained.
        """
        if not self.is_trained:
            return None

        features = np.array(
            [getattr(window, col) for col in FEATURE_COLUMNS],
            dtype=np.float32,
        )

        ae_result = self.autoencoder.predict(features)
        if_result = self.iforest.predict(features)

        # Ensemble: flag if autoencoder says anomaly
        # Boost severity if both agree
        is_anomaly = ae_result["is_anomaly"]
        severity = ae_result["severity"]
        if is_anomaly and if_result["is_anomaly"]:
            severity = min(severity * 1.3, 1.0)  # both agree → boost confidence

        result = {
            "is_anomaly": is_anomaly,
            "severity": round(severity, 3),
            "autoencoder": ae_result,
            "isolation_forest": if_result,
        }

        # Persist anomaly if detected
        if is_anomaly:
            self._store_anomaly(window, result)

        return result

    def _store_anomaly(self, window: MetricWindow, result: dict):
        db = SessionLocal()
        try:
            anomaly = Anomaly(
                app_name=window.app_name,
                endpoint=window.endpoint,
                detected_at=datetime.now(timezone.utc),
                severity=result["severity"],
                anomaly_score=result["autoencoder"]["anomaly_score"],
                detector="ensemble",
                feature_contributions=result["autoencoder"]["top_contributing_features"],
                window_data={col: getattr(window, col) for col in FEATURE_COLUMNS},
            )
            db.add(anomaly)
            db.commit()
        finally:
            db.close()