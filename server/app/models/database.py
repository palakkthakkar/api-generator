from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from ..config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class MetricWindow(Base):
    """Aggregated metrics for one endpoint in one time window."""
    __tablename__ = "metric_windows"
    
    id = Column(Integer, primary_key=True)
    app_name = Column(String, index=True)
    endpoint = Column(String, index=True)
    window_start = Column(DateTime, index=True)
    
    # Aggregated features (these become ML input)
    request_count = Column(Integer)
    error_count = Column(Integer)
    error_rate = Column(Float)
    latency_p50 = Column(Float)
    latency_p95 = Column(Float)
    latency_p99 = Column(Float)
    latency_mean = Column(Float)
    latency_std = Column(Float)
    avg_request_size = Column(Float)
    avg_response_size = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Anomaly(Base):
    """Detected anomaly record."""
    __tablename__ = "anomalies"
    
    id = Column(Integer, primary_key=True)
    app_name = Column(String, index=True)
    endpoint = Column(String, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    severity = Column(Float)              # 0.0 - 1.0
    anomaly_score = Column(Float)         # raw reconstruction error
    detector = Column(String)             # "autoencoder" or "isolation_forest"
    feature_contributions = Column(JSON)  # which features deviated most
    window_data = Column(JSON)            # snapshot of the metric window
    resolved = Column(Boolean, default=False)


# Create tables
Base.metadata.create_all(engine)