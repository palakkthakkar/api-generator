"""
Isolation Forest — unsupervised anomaly detector.
Complements the autoencoder. If BOTH flag an anomaly, confidence is higher.
"""

import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class IsolationForestDetector:
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.model = None
        self.scaler = StandardScaler()

    def train(self, data: np.ndarray, contamination: float = 0.05):
        """
        Train on normal data.
        contamination: expected fraction of anomalies (5% default).
        """
        scaled = self.scaler.fit_transform(data)
        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(scaled)
        self._save()
        print(f"  IsolationForest trained on {len(data)} windows.")

    def predict(self, window_features: np.ndarray) -> dict:
        if self.model is None:
            self._load()
        scaled = self.scaler.transform(window_features.reshape(1, -1))
        score = self.model.decision_function(scaled)[0]
        prediction = self.model.predict(scaled)[0]  # 1 = normal, -1 = anomaly

        return {
            "is_anomaly": bool(prediction == -1),
            "anomaly_score": round(float(-score), 4),  # negate so higher = more anomalous
        }

    def _save(self):
        joblib.dump({"model": self.model, "scaler": self.scaler}, self.model_dir / "iforest.pkl")

    def _load(self):
        checkpoint = joblib.load(self.model_dir / "iforest.pkl")
        self.model = checkpoint["model"]
        self.scaler = checkpoint["scaler"]