"""
Autoencoder for learning "normal" API behavior.
Input: 10-dimensional feature vector (one metric window)
Architecture: 10 → 32 → 16 → 8 → 16 → 32 → 10
Anomaly = high reconstruction error
"""

import torch
import torch.nn as nn
import numpy as np
from pathlib import Path


class AnomalyAutoencoder(nn.Module):
    def __init__(self, input_dim: int = 10):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8),      # bottleneck
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, input_dim),
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Per-sample MSE reconstruction error."""
        with torch.no_grad():
            reconstructed = self.forward(x)
            error = torch.mean((x - reconstructed) ** 2, dim=1)
        return error

    def feature_contributions(self, x: torch.Tensor) -> torch.Tensor:
        """Per-feature squared error — shows WHICH features deviated."""
        with torch.no_grad():
            reconstructed = self.forward(x)
            contributions = (x - reconstructed) ** 2
        return contributions


class AutoencoderTrainer:
    """Handles training, saving, loading, and inference."""

    FEATURE_NAMES = [
        "request_count", "error_count", "error_rate",
        "latency_p50", "latency_p95", "latency_p99",
        "latency_mean", "latency_std",
        "avg_request_size", "avg_response_size",
    ]

    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.scaler_mean = None
        self.scaler_std = None

    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Z-score normalization. Store stats for inference."""
        if self.scaler_mean is None:
            self.scaler_mean = data.mean(axis=0)
            self.scaler_std = data.std(axis=0) + 1e-8  # avoid div by zero
        return (data - self.scaler_mean) / self.scaler_std

    def train(self, data: np.ndarray, epochs: int = 100, lr: float = 1e-3):
        """
        Train the autoencoder on normal traffic data.
        data: shape (n_windows, 10) — metric windows from PostgreSQL
        """
        # Normalize
        normalized = self._normalize(data)
        tensor = torch.FloatTensor(normalized).to(self.device)
        dataset = torch.utils.data.TensorDataset(tensor)
        loader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)

        self.model = AnomalyAutoencoder(input_dim=data.shape[1]).to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.MSELoss()

        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for (batch,) in loader:
                optimizer.zero_grad()
                reconstructed = self.model(batch)
                loss = criterion(reconstructed, batch)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            scheduler.step()
            if (epoch + 1) % 20 == 0:
                avg_loss = total_loss / len(loader)
                print(f"  Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.6f}")

        # Compute threshold from training data (mean + 2*std of errors)
        self.model.eval()
        errors = self.model.reconstruction_error(tensor).cpu().numpy()
        self.threshold = float(errors.mean() + 2 * errors.std())
        print(f"  Trained. Threshold: {self.threshold:.4f}")

        self._save()

    def predict(self, window_features: np.ndarray) -> dict:
        """
        Score a single metric window.
        Returns: {is_anomaly, score, severity, feature_contributions}
        """
        if self.model is None:
            self._load()

        normalized = (window_features - self.scaler_mean) / self.scaler_std
        tensor = torch.FloatTensor(normalized).unsqueeze(0).to(self.device)

        self.model.eval()
        error = self.model.reconstruction_error(tensor).item()
        contributions = self.model.feature_contributions(tensor).squeeze().cpu().numpy()

        is_anomaly = error > self.threshold
        severity = min(error / self.threshold, 1.0) if self.threshold > 0 else 0.0

        # Map contributions to feature names
        top_features = sorted(
            zip(self.FEATURE_NAMES, contributions.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": round(error, 4),
            "threshold": round(self.threshold, 4),
            "severity": round(severity, 3),
            "top_contributing_features": [
                {"feature": name, "deviation": round(val, 4)}
                for name, val in top_features[:3]
            ],
        }

    def _save(self):
        torch.save({
            "model_state": self.model.state_dict(),
            "scaler_mean": self.scaler_mean,
            "scaler_std": self.scaler_std,
            "threshold": self.threshold,
        }, self.model_dir / "autoencoder.pt")

    def _load(self):
        checkpoint = torch.load(self.model_dir / "autoencoder.pt", map_location=self.device)
        self.model = AnomalyAutoencoder().to(self.device)
        self.model.load_state_dict(checkpoint["model_state"])
        self.scaler_mean = checkpoint["scaler_mean"]
        self.scaler_std = checkpoint["scaler_std"]
        self.threshold = checkpoint["threshold"]
        self.model.eval()