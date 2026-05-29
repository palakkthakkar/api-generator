from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql://postgres:Sarika%40123@localhost:5432/postgres"
    
    # ML config
    anomaly_threshold: float = 2.0       # reconstruction error multiplier
    aggregation_window_sec: int = 60     # 1-minute rolling windows
    min_training_windows: int = 3        # minimum data points before training (lowered for demo)
    retrain_interval_min: int = 30       # retrain every 30 minutes
    
    class Config:
        env_file = ".env"

settings = Settings()