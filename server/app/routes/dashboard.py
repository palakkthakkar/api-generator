from fastapi import APIRouter, Query
from datetime import datetime, timedelta, timezone
from ..models.database import SessionLocal, MetricWindow, Anomaly

router = APIRouter(prefix="/api/v1/dashboard")


@router.get("/endpoints")
def list_endpoints():
    """List all monitored endpoints with their latest stats."""
    db = SessionLocal()
    try:
        # Get distinct endpoints
        results = db.query(
            MetricWindow.app_name,
            MetricWindow.endpoint
        ).distinct().all()

        endpoints = []
        for app_name, endpoint in results:
            latest = (
                db.query(MetricWindow)
                .filter_by(app_name=app_name, endpoint=endpoint)
                .order_by(MetricWindow.window_start.desc())
                .first()
            )
            if latest:
                endpoints.append({
                    "app_name": app_name,
                    "endpoint": endpoint,
                    "latest_p95": latest.latency_p95,
                    "latest_error_rate": latest.error_rate,
                    "latest_rps": latest.request_count,
                })
        return {"endpoints": endpoints}
    finally:
        db.close()


@router.get("/metrics/{app_name}/{endpoint:path}")
def get_metrics(app_name: str, endpoint: str, hours: int = Query(1, ge=1, le=72)):
    """Get time-series metrics for a specific endpoint."""
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        windows = (
            db.query(MetricWindow)
            .filter(
                MetricWindow.app_name == app_name,
                MetricWindow.endpoint == endpoint,
                MetricWindow.window_start >= since,
            )
            .order_by(MetricWindow.window_start)
            .all()
        )
        return {
            "endpoint": endpoint,
            "data": [
                {
                    "timestamp": w.window_start.isoformat(),
                    "request_count": w.request_count,
                    "error_rate": w.error_rate,
                    "latency_p50": w.latency_p50,
                    "latency_p95": w.latency_p95,
                    "latency_p99": w.latency_p99,
                }
                for w in windows
            ],
        }
    finally:
        db.close()


@router.get("/anomalies")
def get_anomalies(hours: int = Query(24, ge=1, le=168)):
    """Get recent anomalies across all endpoints."""
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        anomalies = (
            db.query(Anomaly)
            .filter(Anomaly.detected_at >= since)
            .order_by(Anomaly.detected_at.desc())
            .limit(100)
            .all()
        )
        return {
            "anomalies": [
                {
                    "id": a.id,
                    "endpoint": a.endpoint,
                    "app_name": a.app_name,
                    "detected_at": a.detected_at.isoformat(),
                    "severity": a.severity,
                    "score": a.anomaly_score,
                    "features": a.feature_contributions,
                }
                for a in anomalies
            ],
        }
    finally:
        db.close()